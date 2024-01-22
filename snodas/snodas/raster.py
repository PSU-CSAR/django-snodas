from __future__ import annotations

import argparse

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

import numpy
import numpy.typing

from osgeo import gdal

from snodas.snodas.constants import SNODAS_ORIGIN_TILE, TILE_PREFIX
from snodas.snodas.coordinates import Pixel, Tile

if TYPE_CHECKING:
    from snodas.snodas.fileinfo import SNODASFileInfo

gdal.UseExceptions()


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


T = TypeVar('T', bound=numpy.generic)


class TiledRaster(Generic[T]):
    def __init__(self: Self, path: Path) -> None:
        self.path: Path = Path(path)

        if not self.path.is_file():
            raise TypeError('not a file')

    def load_tile(self: Self, tile: Tile) -> numpy.typing.NDArray[T]:
        array: numpy.typing.NDArray[T] = load_tile(self.path, tile)
        return array


class AreaRaster(TiledRaster[numpy.float32]):
    pass


class SNODASRaster(TiledRaster[numpy.int16]):
    def __init__(self: Self, fileinfo: SNODASFileInfo) -> None:
        super().__init__(fileinfo.path)
        self.fileinfo = fileinfo


@dataclass
class AOIRaster:
    array: numpy.typing.NDArray[numpy.float32]
    intersected_tiles: list[Tile]
    origin: Pixel
    min_elevation: float
    max_elevation: float

    @classmethod
    def open(
        cls: type[Self],
        path: Path,
    ) -> Self:
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
                'AOI Raster is empty or could not be opened',
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

    def _load_raster_tile_into_array(
        self: Self,
        raster: TiledRaster,
        array: numpy.typing.NDArray[Any],
        tile: Tile,
    ) -> None:
        tile_origin = tile.origin()
        offset_row = tile_origin.row - self.origin.row
        offset_col = tile_origin.col - self.origin.col
        array[
            offset_row : offset_row + tile.size,
            offset_col : offset_col + tile.size,
        ] = raster.load_tile(tile)

    def load_raster_tiles_into_array(
        self: Self,
        raster: TiledRaster,
        array: numpy.typing.NDArray[Any],
    ) -> None:
        for tile in self.intersected_tiles:
            self._load_raster_tile_into_array(raster, array, tile)


@dataclass
class AOIRasterWithArea(AOIRaster):
    area: numpy.typing.NDArray[numpy.float32]

    @classmethod
    def from_aoi_raster(
        cls: type[Self],
        aoi_raster: AOIRaster,
        area_raster: AreaRaster,
    ) -> Self:
        area = numpy.zeros_like(
            aoi_raster.array,
            dtype=numpy.float32,
        )
        aoi_raster.load_raster_tiles_into_array(area_raster, area)
        return cls(
            area=area,
            array=aoi_raster.array,
            intersected_tiles=aoi_raster.intersected_tiles,
            origin=aoi_raster.origin,
            min_elevation=aoi_raster.min_elevation,
            max_elevation=aoi_raster.max_elevation,
        )


geotransform_type = tuple[float, float, float, float, float, float]


@dataclass
class DEM:
    array: numpy.typing.NDArray[numpy.float32]
    datatype: int
    geotransform: geotransform_type
    srs: str
    nodata: float

    @classmethod
    def open(cls: type[Self], path: Path) -> Self:
        ds: gdal.Dataset = gdal.Open(str(path))
        band: gdal.Band = ds.GetRasterBand(1)
        array: numpy.typing.NDArray[numpy.float32] | None = band.ReadAsArray()

        if array is None:
            raise argparse.ArgumentTypeError(
                'DEM dataset is empty or could not be opened',
            )

        srs: str = ds.GetProjection()
        geotransform: geotransform_type = ds.GetGeoTransform()
        datatype: int = band.DataType
        nodata: float = band.GetNoDataValue()

        del band
        del ds

        return cls(
            array=array,
            datatype=datatype,
            geotransform=geotransform,
            srs=srs,
            nodata=nodata,
        )
