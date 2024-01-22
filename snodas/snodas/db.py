from collections.abc import Iterator
from datetime import date
from functools import cache
from itertools import product
from pathlib import Path
from typing import Self

import numpy
import numpy.typing

from osgeo import gdal, ogr, osr

from snodas import types
from snodas.snodas import constants
from snodas.snodas.aoi import AOI
from snodas.snodas.coordinates import Pixel, Tile
from snodas.snodas.fileinfo import Product
from snodas.snodas.input_rasters import SNODASInputRasterSet
from snodas.snodas.raster import DEM, AOIRaster, AreaRaster

gdal.UseExceptions()


def make_geometry_mask(
    geometry: ogr.Geometry,
    target_raster: gdal.Dataset,
) -> numpy.typing.NDArray[numpy.bool_]:
    f_srs: str = geometry.GetSpatialReference()

    g_srs = osr.SpatialReference()
    g_srs.ImportFromWkt(target_raster.GetProjectionRef())

    if str(g_srs) != str(f_srs):
        raise Exception(
            f'Rasterize failed, f_srs != g_srs: {f_srs} != {g_srs}',
        )

    f_driver: ogr.Driver = ogr.GetDriverByName('Memory')
    f_ds: ogr.DataSource = f_driver.CreateDataSource('wrk')
    f_layer: ogr.Layer = f_ds.CreateLayer('lyr', srs=f_srs)

    feature = ogr.Feature(f_layer.GetLayerDefn())
    feature.SetGeometry(geometry)
    f_layer.CreateFeature(feature)

    g_driver: gdal.Driver = gdal.GetDriverByName('MEM')
    g_ds: gdal.Dataset = g_driver.Create(
        '',
        target_raster.RasterXSize,
        target_raster.RasterYSize,
        1,
        gdal.GDT_Byte,
    )

    g_ds.SetProjection(target_raster.GetProjection())
    g_ds.SetGeoTransform(target_raster.GetGeoTransform())

    gdal.RasterizeLayer(g_ds, (1,), f_layer, burn_values=(1,))

    band: gdal.Band = g_ds.GetRasterBand(1)
    array: numpy.typing.NDArray[numpy.int8] | None = band.ReadAsArray()

    if array is None:
        raise Exception('Rasterization failed, no array returned from band')

    del band
    del g_ds
    del f_layer
    del f_ds

    return array.astype(bool)


def write_aoi_raster(
    path: Path,
    aoi: AOI,
    dem: DEM,
    start_tile: Tile,
    end_tile: Tile,
    intersected_quadkeys: dict[str, str],
) -> None:
    origin = start_tile.origin()
    antiorigin = end_tile.antiorigin()
    origin_latlon = origin.to_latlon()

    mem_driver: gdal.Driver = gdal.GetDriverByName('MEM')
    dataset: gdal.Dataset = mem_driver.Create(
        '',
        antiorigin.col - origin.col,
        antiorigin.row - origin.row,
        1,
        dem.datatype,
    )
    dataset.SetGeoTransform(
        (
            origin_latlon.lon,
            constants.PX_SIZE,
            0,
            origin_latlon.lat,
            0,
            -constants.PX_SIZE,
        ),
    )
    dataset.SetProjection(dem.srs)
    metadata = {constants.SNODAS_ORIGIN_TILE: start_tile.quadkey}
    metadata.update(intersected_quadkeys)
    dataset.SetMetadata(metadata)

    aoi_mask = make_geometry_mask(aoi.geometry, dataset)

    band: gdal.Band = dataset.GetRasterBand(1)

    masked = numpy.where(
        aoi_mask,
        dem.array[
            origin.row : antiorigin.row,
            origin.col : antiorigin.col,
        ],
        dem.nodata,
    )

    # floating points stuff messes up nodata
    masked = numpy.where(
        masked > -10000,
        masked,
        dem.nodata,
    )

    band.WriteArray(masked)
    band.SetNoDataValue(dem.nodata)
    band.ComputeStatistics(approx_ok=False)
    band.FlushCache()
    del band

    # I don't think overviews are useful, but they could be added like
    # dataset.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64])  # noqa: ERA001
    gtiff_driver: gdal.Driver = gdal.GetDriverByName('GTiff')
    outds: gdal.Dataset = gtiff_driver.CreateCopy(
        path,
        dataset,
        options=(
            'COPY_SRC_OVERVIEWS=YES',
            f'BLOCKXSIZE={constants.TILE_SIZE}',
            f'BLOCKYSIZE={constants.TILE_SIZE}',
            'TILED=YES',
            'COMPRESS=DEFLATE',
            'PREDICTOR=3',
            'ZLEVEL=12',
        ),
    )

    del dataset
    del outds


class RasterDatabase:
    def __init__(self: Self, path: Path) -> None:
        self.path = path
        self._aoi_rasters = self.path / 'aoi-rasters'
        self._cogs = self.path / 'cogs'
        self._area_raster = self.path / 'areas.tif'
        self._dem = self.path / 'dem.tif'

    def validate(self: Self) -> Self:
        if not self.path.exists():
            raise FileNotFoundError(f'Unable to read directory: {self.path}')

        if not self.path.is_dir():
            raise ValueError(f'Not a directory: {self.path}')

        return self

    @classmethod
    def create(
        cls: type[Self],
        path: Path,
        input_dem_path: Path,
        force: bool = False,
    ) -> Self:
        self = cls(path)

        try:
            self.path.mkdir(exist_ok=force)
            self._aoi_rasters.mkdir(exist_ok=force)
            self._cogs.mkdir(exist_ok=force)
            self.make_area_raster(force=force)
            self.create_resampled_dem(input_dem_path, force=force)
        except FileExistsError as e:
            raise FileExistsError(
                f'Could not create SNODAS database: {self.path} already exists. '
                'Remove and try again or use `force=True`.',
            ) from e

        return self

    def area_raster(self: Self) -> AreaRaster:
        return AreaRaster(self._area_raster)

    def make_area_raster(self: Self, force: bool = False) -> None:
        if not force and self._area_raster.exists():
            raise FileExistsError(
                'Could not create area raster: '
                f'{self._area_raster} already exists. '
                'Remove and try again or use `force=True`.',
            )

        area_array = numpy.fromiter(
            (
                Pixel(row=x, col=y).area()
                for x, y in product(range(constants.ROWS), range(constants.COLS))
            ),
            dtype=numpy.float32,
        ).reshape(constants.ROWS, constants.COLS)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)

        mem_driver: gdal.Driver = gdal.GetDriverByName('MEM')
        dataset: gdal.Dataset = mem_driver.Create(
            '',
            constants.COLS,
            constants.ROWS,
            1,
            gdal.GDT_Float32,
        )
        dataset.SetGeoTransform(
            (
                constants.ORIGIN_X,
                constants.PX_SIZE,
                0,
                constants.ORIGIN_Y,
                0,
                -constants.PX_SIZE,
            ),
        )
        dataset.SetProjection(srs.ExportToWkt())

        band: gdal.Band = dataset.GetRasterBand(1)
        band.WriteArray(area_array)
        band.FlushCache()
        del band

        gtiff_driver: gdal.Driver = gdal.GetDriverByName('GTiff')
        outds: gdal.Dataset = gtiff_driver.CreateCopy(
            self._area_raster,
            dataset,
            options=(
                'COPY_SRC_OVERVIEWS=YES',
                f'BLOCKXSIZE={constants.TILE_SIZE}',
                f'BLOCKYSIZE={constants.TILE_SIZE}',
                'TILED=YES',
                'COMPRESS=DEFLATE',
                'PREDICTOR=3',
                'ZLEVEL=12',
            ),
        )

        del dataset
        del outds

    def create_resampled_dem(
        self: Self,
        input_dem_path: Path,
        force: bool = False,
    ) -> None:
        self.resample_to_snodas_grid(input_dem_path, self._dem, force=force)

    @staticmethod
    def resample_to_snodas_grid(
        input_raster_path: Path,
        output_raster_path: Path,
        force: bool = False,
    ) -> None:
        if not force and output_raster_path.exists():
            raise FileExistsError(
                'Could not create output raster: '
                f'{output_raster_path} already exists. '
                'Remove and try again or use `force=True`.',
            )

        gdal.Warp(
            output_raster_path,
            input_raster_path,
            format='COG',
            outputBounds=(
                constants.ORIGIN_X,
                constants.ANTIORIGIN_Y,
                constants.ANTIORIGIN_X,
                constants.ORIGIN_Y,
            ),
            outputBoundsSRS='EPSG:4326',
            dstSRS='EPSG:4326',
            width=constants.COLS,
            height=constants.ROWS,
            multithread=True,
            resampleAlg='average',
            creationOptions={
                'BLOCKSIZE': constants.TILE_SIZE,
                'PREDICTOR': 2,
                'RESAMPLING': 'AVERAGE',
                'COMPRESS': 'DEFLATE',
                'LEVEL': 12,
            },
        )

    @staticmethod
    def _format_date(date: date) -> str:
        return date.strftime('%Y%m%d')

    def raster_paths_from_query(
        self: Self,
        query: types.DateQuery,
        product: Product,
    ) -> Iterator[Path]:
        for date_ in query.generate_sequence():
            matching_files = list(
                (self._cogs / self._format_date(date_)).glob(product.to_glob()),
            )

            if len(matching_files) < 1:
                continue
            if len(matching_files) > 1:
                raise RuntimeError(
                    'Found mutliple files matching date / product '
                    f"'{date_}' / '{product.value}': {matching_files}",
                )

            yield matching_files[0]

    def aoi_raster_path_from_triplet(
        self: Self,
        station_triplet: types.StationTriplet,
    ) -> Path:
        return self._aoi_rasters / f'{station_triplet.replace(":", "_")}.tif'

    def rasterize_aoi(self, aoi: AOI, force: bool = False) -> AOIRaster:
        path = self.aoi_raster_path_from_triplet(aoi.station_triplet)
        if not force and path.exists():
            raise FileExistsError(
                f'Could not create AOI raster: {path} already exists. '
                'Remove and try again or use `force=True`.',
            )

        ul_tile, br_tile = aoi.to_tile_extent()

        intersected: dict[str, str] = {}
        index: int = 0
        for tile_row in range(ul_tile.row, br_tile.row + 1):
            for tile_col in range(ul_tile.col, br_tile.col + 1):
                tile = Tile(row=tile_row, col=tile_col)
                geom = tile.to_geom()
                if geom.Intersects(aoi.geometry):
                    intersected[f'{constants.TILE_PREFIX}_{str(index).zfill(3)}'] = (
                        tile.quadkey
                    )
                    index += 1

        write_aoi_raster(
            path,
            aoi,
            DEM.open(self._dem),
            ul_tile,
            br_tile,
            intersected,
        )

        return AOIRaster.open(path)

    def import_snodas_rasters(
        self: Self,
        rasters: SNODASInputRasterSet,
        force: bool = False,
    ) -> None:
        output_dir = self._cogs / self._format_date(rasters.date)

        try:
            output_dir.mkdir(exist_ok=force)
        except FileExistsError as e:
            raise FileExistsError(
                'Could not create SNODAS raster dir: '
                f'{output_dir} already  exists. '
                'Remove directory and try again, or use `force=True`.',
            ) from e

        for raster in rasters:
            raster.write_cog(output_dir=output_dir, force=force)


@cache
def get_raster_database(path: Path) -> RasterDatabase:
    return RasterDatabase(path).validate()
