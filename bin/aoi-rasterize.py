#!/usr/bin/env python
import argparse
import json

from dataclasses import dataclass
from pathlib import Path
from typing import Self

import numpy.typing

from osgeo import gdal, ogr, osr

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
            mask: int = 1 << idx
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
        ring.AddPoint(xmax, ymax)
        ring.AddPoint(xmin, ymax)
        ring.AddPoint(xmin, ymin)
        ring.AddPoint(xmax, ymin)
        ring.AddPoint(xmax, ymax)

        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)

        return poly


@dataclass
class AOI:
    geom: ogr.Geometry

    @classmethod
    def from_pourpoint_geojson(cls, path: str) -> Self:
        geojson = json.loads(Path(path).read_text())
        try:
            geom = [
                g
                for g in geojson["geometries"]
                if g["type"] in ("MultiPolygon", "Polygon")
            ][0]
        except Exception:
            raise argparse.ArgumentTypeError(
                "AOI file does not seem to contain a valid 2D geometry",
            )

        return cls(geom=ogr.CreateGeometryFromJson(json.dumps(geom)))


    def to_tile_extent(self: Self) -> tuple[Tile, Tile]:
        xmin, xmax, ymin, ymax = self.geom.GetEnvelope()
        upperleft = LatLon(lat=ymax, lon=xmin).to_pixel()
        bottomright = LatLon(lat=ymin, lon=xmax).to_pixel()
        # TODO: check intersection with SNODAS grid
        return upperleft.to_tile(), bottomright.to_tile()


@dataclass
class DEM:
    array: numpy.typing.NDArray[numpy.float32]
    datatype: int
    geotransform: tuple[float, float, float, float, float, float]
    srs: str
    nodata: float

    @classmethod
    def open(cls: type[Self], path: str) -> Self:
        ds: gdal.Dataset = gdal.Open(path)
        band: gdal.Band = ds.GetRasterBand(1)
        array: numpy.typing.NDArray[numpy.float32] | None = band.ReadAsArray()

        if array is None:
            raise argparse.ArgumentTypeError(
                "DEM dataset is empty or could not be opened",
            )

        srs: str = ds.GetProjection()

        return cls(
            array=array,
            datatype=band.DataType,
            geotransform=ds.GetGeoTransform(),
            srs=srs,
            nodata=band.GetNoDataValue(),
        )


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
        raise Exception(f'Rasterization failed, no array returned from band')

    del band
    del g_ds
    del f_layer
    del f_ds

    return array.astype(bool)


def write_output(
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

    driver: gdal.Driver = gdal.GetDriverByName('MEM')
    dataset: gdal.Dataset = driver.Create(
        '',
        antiorigin.col - origin.col,
        antiorigin.row - origin.row,
        1,
        dem.datatype,
    )
    dataset.SetGeoTransform((
        origin_latlon.lon,
        PX_SIZE,
        0,
        origin_latlon.lat,
        0,
        -PX_SIZE,
    ))
    dataset.SetProjection(dem.srs)
    metadata = {SNODAS_ORIGIN_TILE: start_tile.quadkey}
    metadata.update(intersected_quadkeys)
    dataset.SetMetadata(metadata)

    aoi_mask = make_geometry_mask(aoi.geom, dataset)

    band: gdal.Band = dataset.GetRasterBand(1)

    masked = numpy.where(
        aoi_mask,
        dem.array[
            origin.row:antiorigin.row,
            origin.col:antiorigin.col,
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
    # dataset.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64])
    driver: gdal.Driver = gdal.GetDriverByName('GTiff')
    outds: gdal.Dataset = driver.CreateCopy(
        path,
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


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'aoi',
        metavar='aoi-geojson-file',
        type=AOI.from_pourpoint_geojson,
        help='Input API goejson file, from the BAGIS pourpoints set',
    )
    parser.add_argument(
        '-d',
        '--dem',
        type=DEM.open,
        required=True,
        help='Path to the SNODAS-resampled DEM raster',
    )
    parser.add_argument(
        '-o',
        '--output-file',
        dest='output_path',
        metavar='outfile',
        type=Path,
        required=True,
        help='Path to the output AOI raster file',
    )
    return parser.parse_args(args=argv)


def main(argv=None) -> None:
    args = parse_args(argv=argv)
    aoi = args.aoi

    ul_tile, br_tile = aoi.to_tile_extent()

    intersected: dict[str, str] = {}
    index: int = 0
    for tile_row in range(ul_tile.row, br_tile.row + 1):
        for tile_col in range(ul_tile.col, br_tile.col + 1):
            tile =Tile(row=tile_row, col=tile_col)
            geom = tile.to_geom()
            if geom.Intersects(aoi.geom):
                intersected[f'{TILE_PREFIX}_{str(index).zfill(3)}'] = tile.quadkey
                index += 1

    write_output(
        args.output_path,
        aoi,
        args.dem,
        ul_tile,
        br_tile,
        intersected,
    )


if __name__ == '__main__':
    main()
