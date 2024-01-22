import json

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from osgeo import gdal, ogr

from snodas import types
from snodas.exceptions import GeoJSONValidationError
from snodas.snodas.coordinates import LatLon, Tile

gdal.UseExceptions()

# geojson type strings
GEOM_COLLECTION = 'GeometryCollection'
FEATURE = 'Feature'
POINT = 'Point'
POLYGON = 'Polygon'
MULTIPOLYGON = 'MultiPolygon'

POLYGON_TYPES = [POLYGON, MULTIPOLYGON]


def join(iterable) -> str:
    return ', '.join(iterable)


@dataclass
class AOI:
    path: Path
    properties: dict[str, Any]
    station_triplet: types.StationTriplet
    name: str
    source: str
    point: dict[str, Any]
    polygon: dict[str, Any] | None = None

    @classmethod
    def from_geojson(cls: type[Self], path: Path | str) -> Self:
        path = Path(path)
        geojson = json.loads(path.read_text())

        kwargs: dict[str, Any] = {}
        try:
            if geojson['type'] == FEATURE:
                if geojson['geometry']['type'] != POINT:
                    raise GeoJSONValidationError(
                        'All pourpoints must have a point geometry.',
                    )
                kwargs['point'] = geojson['geometry']
            elif geojson['type'] == GEOM_COLLECTION:
                geoms: Any = geojson['geometries']

                if len(geoms) != 2:
                    raise GeoJSONValidationError(
                        'Multi-geometry pourpoints cannot have '
                        'more than two geometries',
                    )

                if geoms[0]['type'] == POINT:
                    kwargs['point'] = geoms[0]
                elif geoms[1]['type'] == POINT:
                    kwargs['point'] = geoms[1]
                else:
                    raise GeoJSONValidationError(
                        'All pourpoints must have a point geometry.',
                    )

                if geoms[0]['type'] in POLYGON_TYPES:
                    kwargs['polygon'] = geoms[0]
                elif geoms[1]['type'] in POLYGON_TYPES:
                    kwargs['polygon'] = geoms[1]
                else:
                    raise GeoJSONValidationError(
                        'Multi-geometry pourpoints must have one '
                        '(Mutli)Polygon geometry',
                    )
            else:
                raise GeoJSONValidationError(
                    f"Incompatible type '{geojson['type']}'",
                )

            kwargs['properties'] = geojson['properties']
            kwargs['station_triplet'] = geojson['id']
            kwargs['name'] = geojson['properties'].get(
                'nwccname',
                geojson['properties']['name'],
            )
            kwargs['source'] = geojson['properties']['source']
        except KeyError as e:
            raise GeoJSONValidationError(
                'Pourpoint missing required property',
            ) from e

        return cls(path=path, **kwargs)

    @property
    def geometry(self: Self) -> ogr.Geometry:
        if not self.polygon:
            raise ValueError('AOI does not have a polygon')

        return ogr.CreateGeometryFromJson(json.dumps(self.polygon))

    def to_tile_extent(self: Self) -> tuple[Tile, Tile]:
        xmin, xmax, ymin, ymax = self.geometry.GetEnvelope()
        upperleft = LatLon(lat=ymax, lon=xmin).to_pixel()
        bottomright = LatLon(lat=ymin, lon=xmax).to_pixel()
        # TODO: check intersection with SNODAS grid
        return upperleft.to_tile(), bottomright.to_tile()

    def insert_sql(
        self: Self,
        table: str,
        allow_update: bool = False,
    ) -> tuple[str, list[str]]:
        fields = ['awdb_id', 'name', 'source', 'point']
        values = ['%s', '%s', '%s', 'ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)']
        params = [self.station_triplet, self.name, self.source, json.dumps(self.point)]

        if self.polygon:
            fields.append('polygon')
            values.append('ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)')
            params.append(json.dumps(self.polygon))

        sql = f'insert into {table} ({join(fields)}) values ({join(values)})'  # noqa: S608

        if allow_update:
            updates = fields[1:]
            excludes = [f'EXCLUDED.{field}' for field in updates]
            sql += ' on conflict (awdb_id) do update set '
            sql += f'({join(updates)}) = ({join(excludes)})'

        return sql, params
