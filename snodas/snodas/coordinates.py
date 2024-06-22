from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from area import ring__area
from osgeo import gdal, ogr

from snodas.snodas.constants import (
    ORIGIN_X,
    ORIGIN_Y,
    PX_SIZE,
    TILE_NATIVE_ZOOM,
    TILE_SIZE,
)

gdal.UseExceptions()


@dataclass
class LatLon:
    lat: float
    lon: float

    def to_pixel(self: Self) -> Pixel:
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

    def to_tile(self: Self, size: int = TILE_SIZE) -> Tile:
        tile_row: int = self.row // size
        tile_col: int = self.col // size
        return Tile(row=tile_row, col=tile_col)

    def to_ring(self: Self) -> Sequence[tuple[float, float]]:
        origin: LatLon = self.to_latlon()
        return (
            (origin.lon, origin.lat),
            (origin.lon + PX_SIZE, origin.lat),
            (origin.lon + PX_SIZE, origin.lat - PX_SIZE),
            (origin.lon, origin.lat - PX_SIZE),
            (origin.lon, origin.lat),
        )

    def area(self: Self) -> float:
        return abs(ring__area(self.to_ring()))


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
                f'Tiles only support native zoom level {TILE_NATIVE_ZOOM}, '
                f'but quadkey is for zoom level {len(quadkey)}.',
            )

        row: int = 0
        col: int = 0
        for idx, char in enumerate(reversed(quadkey)):
            mask: int = 1 << idx
            match char:
                case '0':
                    continue
                case '1':
                    col |= mask
                case '2':
                    row |= mask
                case '3':
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
                + int(bool(self.row & (1 << (z_level - 1)))) * 2,
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
        origin: LatLon = self.origin().to_latlon()
        br: LatLon = Pixel(
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
