#!/usr/bin/env python
import argparse

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Self, Sequence

import numpy

from area import ring__area
from osgeo import gdal, osr

gdal.UseExceptions()

# new SNODAS grid values
ORIGIN_X = -124.733333333333333
ORIGIN_Y = 52.875000000000000
PX_SIZE = 0.008333333333333
COLS=6935
ROWS=3351
TILE_SIZE=256


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
        lat: float = ORIGIN_Y - (self.row * PX_SIZE)
        lon: float = ORIGIN_X + (self.col * PX_SIZE)
        return LatLon(lat=lat, lon=lon)

    def to_ring(self: Self) -> Sequence[tuple[float, float]]:
        origin = self.to_latlon()
        return (
            (origin.lon, origin.lat),
            (origin.lon + PX_SIZE, origin.lat),
            (origin.lon + PX_SIZE, origin.lat - PX_SIZE),
            (origin.lon, origin.lat - PX_SIZE),
            (origin.lon, origin.lat),
        )

    def area(self: Self) -> float:
        return abs(ring__area(self.to_ring()))


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o',
        '--output',
        help='Path to output area raster',
        required=True,
        type=Path,
    )
    return parser.parse_args(args=argv)


def main(argv=None) -> None:
    args = parse_args(argv=argv)

    area_array = numpy.fromiter(
        (
            Pixel(row=x, col=y).area()
            for x, y in product(range(ROWS), range(COLS))
        ),
        dtype=numpy.float32,
    ).reshape(ROWS, COLS)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    driver: gdal.Driver = gdal.GetDriverByName('MEM')
    dataset: gdal.Dataset = driver.Create(
        '',
        COLS,
        ROWS,
        1,
        gdal.GDT_Float32,
    )
    dataset.SetGeoTransform((
        ORIGIN_X,
        PX_SIZE,
        0,
        ORIGIN_Y,
        0,
        -PX_SIZE,
    ))
    dataset.SetProjection(srs.ExportToWkt())

    band: gdal.Band = dataset.GetRasterBand(1)
    band.WriteArray(area_array)
    band.FlushCache()
    del band

    driver: gdal.Driver = gdal.GetDriverByName('GTiff')
    outds: gdal.Dataset = driver.CreateCopy(
        args.output,
        dataset,
        options=(
            "COPY_SRC_OVERVIEWS=YES",
            f"BLOCKXSIZE={TILE_SIZE}",
            f"BLOCKYSIZE={TILE_SIZE}",
            "TILED=YES",
            "COMPRESS=DEFLATE",
            "PREDICTOR=3",
            "ZLEVEL=12",
        ),
    )

    del dataset
    del outds


if __name__ == '__main__':
    main()
