import csv

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import IO, Self

import numpy
import numpy.typing

from snodas import types
from snodas.snodas.constants import NODATA
from snodas.snodas.elevation_band import ElevationBand
from snodas.snodas.fileinfo import Product
from snodas.snodas.raster import AOIRasterWithArea, SNODASRaster
from snodas.snodas.raster_collection import RasterCollection


@dataclass
class Result:
    date: date
    elevation_band: ElevationBand
    product: Product
    mean: float
    area: float


class ZonalStats:
    def __init__(
        self: Self,
        products: set[Product],
        elevation_bands: tuple[ElevationBand, ...],
        dates: tuple[date, ...],
        *results: Result,
    ) -> None:
        self._products_index = {
            product: idx + 1 for idx, product in enumerate(sorted(products))
        }
        self._elevation_bands_index = {
            band: idx for idx, band in enumerate(sorted(elevation_bands))
        }
        self._dates_index = {dt: idx for idx, dt in enumerate(sorted(dates))}
        self._array = numpy.full(
            (
                len(self._dates_index),
                len(self._elevation_bands_index),
                len(self._products_index) + 1,
            ),
            -numpy.inf,
            dtype=numpy.float32,
        )

        self.add_results(*results)

    def add_result(self: Self, result: Result) -> None:
        zone = self._array[self._dates_index[result.date]][
            self._elevation_bands_index[result.elevation_band]
        ]

        zone[0] = result.area
        zone[self._products_index[result.product]] = result.mean

    def add_results(self: Self, *results: Result) -> None:
        for result in results:
            self.add_result(result)

    def validate(self: Self) -> None:
        if (self._array == -numpy.inf).any():
            raise ValueError(
                'Results array is incomplete. '
                'Ensure all data was processed and added to results successfully.',
            )

    def dump(self: Self) -> list[types.SnodasZonalStats]:
        self.validate()
        stats: list[types.SnodasZonalStats] = []
        for date_, date_idx in self._dates_index.items():
            zones: list[types.SnodasZonalStat] = []
            for band, band_idx in self._elevation_bands_index.items():
                results = {
                    'area_m2': self._array[date_idx][band_idx][0],
                }
                for product, product_idx in self._products_index.items():
                    unit = product.unit()
                    results[f'mean_{product}_{unit.name}'] = unit.scale(
                        self._array[date_idx][band_idx][product_idx],
                    )
                zones.append(
                    types.SnodasZonalStat(
                        min_elevation_ft=band.min,
                        max_elevation_ft=band.max,
                        **results,
                    ),
                )
            stats.append(
                types.SnodasZonalStats(
                    date=date_,
                    zones=zones,
                ),
            )
        return stats

    def dump_to_csv(self: Self, out: IO) -> None:
        writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)

        headers: list[str] = ['date']
        for band in self._elevation_bands_index:
            headers.append(f'area_m2_{band}')
            for product in self._products_index:
                headers.append(f'{product.value}_{product.unit().name}_{band}')

        writer.writerow(headers)

        for date_, date_idx in self._dates_index.items():
            row: list[str] = [date_.isoformat()]
            for band_idx in self._elevation_bands_index.values():
                # area
                row.append(
                    self._array[date_idx][band_idx][0],
                )
                for product, product_idx in self._products_index.items():
                    unit = product.unit()
                    row.append(
                        str(
                            unit.scale(self._array[date_idx][band_idx][product_idx]),
                        ),
                    )
            writer.writerow(row)

    @classmethod
    def calculate(
        cls: type[Self],
        aoi: AOIRasterWithArea,
        snodas_rasters: RasterCollection,
        elevation_band_step_feet: int = 1000,
    ) -> Self:
        aoi = aoi
        elevation_bands = tuple(
            ElevationBand.generate(
                size_ft=elevation_band_step_feet,
            ),
        )

        results: list[Result] = []
        for raster in snodas_rasters:
            # if we're going to introduce parallelism it would be here
            # sharing the aoi and area arrays might be tricky, see
            # https://stackoverflow.com/a/72437073
            # probably want to make parallelism conditional on the
            # size of raster set (like < 50 don't pay the parallel tax)
            results.extend(cls._calc(aoi, raster, elevation_bands))

        return cls(
            snodas_rasters.products,
            elevation_bands,
            tuple(snodas_rasters.dates),
            *results,
        )

    @staticmethod
    def _calc(
        aoi: AOIRasterWithArea,
        snodas: SNODASRaster,
        elevation_bands: Iterable[ElevationBand],
    ) -> list[Result]:
        date_ = snodas.fileinfo.datetime.date()
        product = snodas.fileinfo.product
        values_array = numpy.empty_like(
            aoi.array,
            dtype=numpy.int16,
        )
        values_array[:] = NODATA

        for tile in aoi.intersected_tiles:
            tile_origin = tile.origin()
            offset_row = tile_origin.row - aoi.origin.row
            offset_col = tile_origin.col - aoi.origin.col
            values_array[
                offset_row : offset_row + tile.size,
                offset_col : offset_col + tile.size,
            ] = snodas.load_tile(tile)

        results: list[Result] = []
        for band in elevation_bands:
            selection: numpy.typing.NDArray[numpy.bool_] = (
                (aoi.array >= band.min_meters)
                & (aoi.array < band.max_meters)
                & (values_array != NODATA)
            )

            if not selection.any():
                results.append(
                    Result(
                        date=date_,
                        product=product,
                        elevation_band=band,
                        mean=numpy.nan,
                        area=0,
                    ),
                )
                continue

            results.append(
                Result(
                    date=date_,
                    product=product,
                    elevation_band=band,
                    mean=float(numpy.average(values_array[selection])),
                    area=float(numpy.average(aoi.area[selection])),
                ),
            )

        return results
