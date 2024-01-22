#!/usr/bin/env python
import argparse
from enum import Enum
import re

from dataclasses import dataclass
from datetime import datetime
from math import floor, ceil
from pathlib import Path
from typing import Any, Generic, Iterator, Self, TypeVar, overload

from numpy import int16

import numpy
import numpy.typing

from osgeo import gdal, ogr

gdal.UseExceptions()

# new SNODAS grid values
ORIGIN_X = -124.733333333333333
ORIGIN_Y = 52.875000000000000
PX_SIZE = 0.008333333333333
COLS=6935
ROWS=3351
TILE_SIZE = 256
TILE_NATIVE_ZOOM = 4
SNODAS_ORIGIN_TILE = 'SNODAS_ORIGIN_TILE'
TILE_PREFIX = 'SNODAS_TILE'
NODATA = -9999

# we use these overall min/max elevation values
# to establish our elevation band ranges
DEM_MIN_M = -84.833877563477
DEM_MAX_M = 4291.7211914062
M_TO_FT = 3.28084
FT_TO_M = 0.3048


@dataclass
class LatLon:
    lat: float
    lon: float

    def to_pixel(self: Self) -> 'Pixel':
        row: int = int((ORIGIN_Y - self.lat) / PX_SIZE)
        col: int = int((self.lon - ORIGIN_X) / PX_SIZE)
        return Pixel(row=row, col=col)


@dataclass
class Pixel:
    row: int
    col: int

    def to_latlon(self: Self) -> LatLon:
        lat = ORIGIN_Y - (self.row * PX_SIZE)
        lon = ORIGIN_X + (self.col * PX_SIZE)
        return LatLon(lat=lat, lon=lon)

    def to_tile(self: Self, size: int = TILE_SIZE) -> 'Tile':
        tile_row = self.row // size
        tile_col = self.col // size
        return Tile(row=tile_row, col=tile_col)


@dataclass
class Tile:
    row: int
    col: int
    zoom: int = TILE_NATIVE_ZOOM
    size: int = TILE_SIZE

    @classmethod
    def from_quadkey(cls: type[Self], quadkey: str) -> Self:
        if len(quadkey) != TILE_NATIVE_ZOOM:
            raise ValueError(
                f"Tiles only support native zoom level {TILE_NATIVE_ZOOM}, "
                f"but quadkey is for zoom level {len(quadkey)}."
            )

        row: int = 0
        col: int = 0
        for idx, char in enumerate(reversed(quadkey)):
            mask = 1 << idx
            match char:
                case "0":
                    continue
                case "1":
                    col |= mask
                case "2":
                    row |= mask
                case "3":
                    row |= mask
                    col |= mask
                case _:
                    raise ValueError(f'Invalid quadkey: {quadkey}')

        return cls(row=row, col=col)

    @property
    def quadkey(self: Self) -> str:
        qk: str = ''

        for z_level in range(self.zoom, 0, -1):
            qk += str(
                int(bool(self.col & (1 << (z_level - 1))))
                + int(bool(self.row & (1 << (z_level - 1)))) * 2
            )

        return qk

    def origin(self: Self) -> Pixel:
        return Pixel(
            row=(self.row * self.size),
            col=(self.col * self.size),
        )

    def antiorigin(self: Self) -> Pixel:
        return Pixel(
            row=((self.row + 1) * self.size),
            col=((self.col + 1) * self.size),
        )

    def to_geom(self: Self) -> ogr.Geometry:
        origin = self.origin().to_latlon()
        br = Pixel(
            row=((self.row + 1) * self.size),
            col=((self.col + 1) * self.size),
        ).to_latlon()
        xmin, ymax = origin.lon, origin.lat
        xmax, ymin = br.lon, br.lat

        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(xmin, ymin)
        ring.AddPoint(xmax, ymin)
        ring.AddPoint(xmax, ymax)
        ring.AddPoint(xmin, ymax)
        ring.AddPoint(xmin, ymin)

        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)

        return poly


@dataclass
class AOIRaster:
    array: numpy.typing.NDArray[numpy.float32]
    intersected_tiles: list[Tile]
    origin: Pixel
    min_elevation: float
    max_elevation: float

    @classmethod
    def open(cls: type[Self], path: str) -> Self:
        ds: gdal.Dataset = gdal.Open(path)
        metadata = ds.GetMetadata()
        intersected_tiles = [
            Tile.from_quadkey(val)
            for key, val in metadata.items()
            if key.startswith(TILE_PREFIX)
        ]
        origin = Tile.from_quadkey(metadata[SNODAS_ORIGIN_TILE]).origin()

        band: gdal.Band = ds.GetRasterBand(1)
        min_: float = band.GetMinimum()
        max_: float = band.GetMaximum()
        array: numpy.typing.NDArray[numpy.float32] | None = band.ReadAsArray()

        if array is None:
            raise argparse.ArgumentTypeError(
                "AOI Raster is empty or could not be opened",
            )

        del band
        del ds

        return cls(
            array=array,
            intersected_tiles=intersected_tiles,
            origin=origin,
            min_elevation=min_,
            max_elevation=max_,
        )


class Region(Enum):
    US = 'us'
    MASKED = 'zz'


class Model(Enum):
    SSM = 'ssm'


class Datatype(Enum):
    V0 = 'v0'  # driving input
    V1 = 'v1'  # model output


class Timecode(Enum):
    T0024 =  '0024'  # 24 hr integration
    T0001 = '0001'  # 1 hr snapshot


class Interval(Enum):
    HOUR = 'H'
    DAY = 'D'


class Offset(Enum):
    P001 = 'P001'  # value is delta over interval or value at interval end
    P000 = 'P000'  # value from interval start


_product_code_to_product_name = {
    1025: 'precip',
    1034: 'swe',
    1036: 'depth',
    1038: 'average_temp',
    1039: 'sublimation_blowing',
    1044: 'runoff',
    1050: 'sublimation',
}


class Product(Enum):
    PRECIP_SOLID = 'precip_solid'
    PRECIP_LIQUID = 'precip_liquid'
    SNOW_WATER_EQUIVALENT = 'swe'
    SNOW_DEPTH = 'depth'
    AVERAGE_TEMP = 'average_temp'
    SUBLIMATION = 'sublimation'
    SUBLIMATION_BLOWING = 'sublimation_blowing'
    RUNOFF = 'runoff'

    @classmethod
    def from_product_codes(cls: type[Self], product_code: int, vcode: str) -> Self:
        product_name = _product_code_to_product_name[product_code]

        if product_name != 'precip':
            return cls(product_name)

        match vcode:
            case 'lL00':
                return cls('precip_liquid')
            case 'lL01':
                return cls('precip_solid')
            case _:
                raise ValueError(
                    f"unknown vcode '{vcode}' for product type 'precip'",
                )


class SNODASFileInfo:
    _match = re.compile(
        r'^'
        r'(?P<region>[a-z]{2})_'
        r'(?P<model>[a-z]{3})'
        r'(?P<datatype>v\d)'
        r'(?P<product_code>\d{4})'
        r'(?P<scaled>S?)'
        r'(?P<vcode>[a-zA-Z]{2}[\d_]{2})'
        r'(?P<timecode>[AT]00[02][14])'
        r'TTNATS'
        r'(?P<year>\d{4})'
        r'(?P<month>\d{2})'
        r'(?P<day>\d{2})'
        r'(?P<hour>\d{2})'
        r'(?P<interval>H|D)'
        r'(?P<offset>P00[01])'
        r'$'
    ).match


    def __init__(self: Self, path: Path) -> None:
        self.name = path.stem
        match = self._match(self.name)

        if not match:
            raise ValueError('unable to parse SNODAS file path')

        info = match.groupdict()

        try:
            self.region = Region(info['region'])
            self.model = Model(info['model'])
            self.datatype = Datatype(info['datatype'])
            self.scaled = info['scaled']
            self.vcode = info['vcode']
            self.timecode = Timecode
            self.datetime = datetime(
                year=int(info['year']),
                month=int(info['month']),
                day=int(info['day']),
                hour=int(info['hour']),
            )
            self.interval = Interval(info['interval'])
            self.offset = Offset(info['offset'])
            self.product = Product.from_product_codes(
                int(info['product_code']),
                self.vcode,
            )
        except Exception:
            raise ValueError('invalid value in SNODAS file name')


class TiledRaster:
    def __init__(self: Self, path: str) -> None:
        self.path = Path(path)

        if not self.path.is_file():
            raise TypeError("not a file")

    def load_tile(self: Self, tile: Tile) -> numpy.typing.NDArray[int16]:
        array: numpy.typing.NDArray[int16] = load_tile(self.path, tile)
        return array


class SNODASFile(TiledRaster):
    def __init__(self: Self, path: str) -> None:
        super().__init__(path)
        self.fileinfo = SNODASFileInfo(self.path)


def load_tile(path: Path, tile: Tile) -> numpy.typing.NDArray[Any]:
    origin = tile.origin()
    ds: gdal.Dataset = gdal.Translate(
        '/vsimem/inmem.tif',
        path,
        bandList=(1,),
        srcWin=(origin.col, origin.row, tile.size, tile.size),
        unscale=True,
    )
    band: gdal.Band = ds.GetRasterBand(1)
    array: numpy.typing.NDArray[Any] | None = band.ReadAsArray()

    if array is None:
        raise Exception(f'Failed to load tile from {path}: {tile}')

    return array


T = TypeVar('T', bound=int | float)


@dataclass
class ElevationBand(Generic[T]):
    min: T
    max: T

    @property
    def min_meters(self: Self) -> float:
        return self.min * FT_TO_M

    @property
    def max_meters(self: Self) -> float:
        return self.max * FT_TO_M

    def __str__(self: Self) -> str:
        return f'{self.min}:{self.max}'

    @overload
    @classmethod
    def generate(
        cls: type[Self],
        size_ft: int,
        min_elevation: int | float = DEM_MIN_M,
        max_elevation: int | float = DEM_MAX_M,
    ) -> Iterator[Self]: ...

    @overload
    @classmethod
    def generate(
        cls: type[Self],
        size_ft: float,
        min_elevation: int | float = DEM_MIN_M,
        max_elevation: int | float = DEM_MAX_M,
    ) -> Iterator[Self]: ...

    @classmethod
    def generate(
        cls: type[Self],
        size_ft: int | float = 1000,
        min_elevation: int | float = DEM_MIN_M,
        max_elevation: int | float = DEM_MAX_M,
    ) -> Iterator[Self]:
        """
        Yields elevation bands of size_ft (default 1000), aligned to 0,
        sufficient to capture elevation range of AOI.

        For example, if an AOI has a min / max elevation of 638.528 / 2328.196
        meters, this function will yield the following tuples given a size_ft
        of 1000:

            (2000, 3000)
            (3000, 4000)
            (4000, 5000)
            (5000, 6000)
            (6000, 7000)
            (7000, 8000)
        """
        if size_ft <= 0:
            yield cls(
                min=int(min_elevation * M_TO_FT),
                max=(int(max_elevation * M_TO_FT) + 1),
            )
        else:
            start = int((min_elevation * M_TO_FT) // size_ft)
            end = int((max_elevation * M_TO_FT) // size_ft ) + 1

            yield from (
                cls(min=(idx * size_ft), max=((idx + 1) * size_ft))
                for idx in range(start, end)
            )


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'aoi',
        metavar='aoi-raster-file',
        type=AOIRaster.open,
        help='Input API Raster file',
    )
    parser.add_argument(
        '-s',
        '--snodas-raster',
        type=str,
        required=True,
        help='Path to the SNODAS variable raster',
    )
    #parser.add_argument(
    #    '-a',
    #    '--area-raster',
    #    type=TiledRaster,
    #    required=True,
    #    help='Path to the SNODAS grid area raster',
    #)
    parser.add_argument(
        '-b',
        '--elevation-band-step-feet',
        type=int,
        default=1000,
        help=(
          'Size of elevation bands used for stats aggregation. '
          'A value of 0 or less will not aggregate by elevation '
          'and return an overall value for the AOI.'
        ),
    )
    parser.add_argument(
        '--omit-empty-elevation-bands',
        action='store_true',
        help=('Exclude empty elevation bands from the output table.')
    )
    return parser.parse_args(args=argv)


def main(argv=None) -> None:
    args = parse_args(argv=argv)
    aoi: AOIRaster = args.aoi
    snodas = SNODASFile(args.snodas_raster)
    #area: TiledRaster = args.area_raster

    #area_array = numpy.zeros_like(aoi.array, dtype=float32)
    values_array = numpy.empty_like(aoi.array, dtype=int16)
    values_array[:] = NODATA

    # TODO: from here down needs to be abstracted,
    # it can be reused for both area and values
    for tile in aoi.intersected_tiles:
        tile_origin = tile.origin()
        offset_row = tile_origin.row - aoi.origin.row
        offset_col = tile_origin.col - aoi.origin.col
        #area_array[
        #    offset_row:offset_row + tile.size,
        #    offset_col:offset_col + tile.size,
        #] = area.load_tile(tile)
        values_array[
            offset_row:offset_row + tile.size,
            offset_col:offset_col + tile.size,
        ] = snodas.load_tile(tile)

    stats: dict[str, float] = {}
    print(ElevationBand.generate(size_ft=args.elevation_band_step_feet))
    for band in ElevationBand.generate(size_ft=args.elevation_band_step_feet):
        colname = f'{snodas.fileinfo.product.value}_{band}'

        if band.max_meters <= aoi.min_elevation:
            if not args.omit_empty_elevation_bands:
                stats[colname] = numpy.nan
            continue

        elif band.min_meters > aoi.max_elevation:
            if args.omit_empty_elevation_bands:
                break

            stats[colname] = numpy.nan
            continue

        stats[colname] = float(numpy.average(
            values_array[
                (aoi.array >= band.min_meters)
                & (aoi.array < band.max_meters)
                & (values_array != NODATA)
            ],
        ))

    print(stats)

    # Output needs to be in CSV format. See existing code.


if __name__ == '__main__':
    main()
