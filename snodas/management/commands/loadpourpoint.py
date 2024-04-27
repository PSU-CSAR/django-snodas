import json

from django.core.management.base import BaseCommand
from django.db import connection

from ...exceptions import GeoJSONValidationError
from ..utils import FullPaths, is_file

TABLE = 'pourpoint.pourpoint'

# geojson type strings
GEOM_COLLECTION = 'GeometryCollection'
FEATURE = 'Feature'
POINT = 'Point'
POLYGON = 'Polygon'
MULTIPOLYGON = 'MultiPolygon'

POLYGON_TYPES = [POLYGON, MULTIPOLYGON]


def join(iterable):
    return ', '.join(iterable)


class Pourpoint:
    def __init__(self, awdb_id, name, source, point, polygon=None):
        self.awdb_id = awdb_id
        self.name = name
        self.source = source
        self.point = point
        self.polygon = polygon

    @classmethod
    def from_geojson(cls, geojson):
        kwargs = {}
        try:
            if geojson['type'] == FEATURE:
                if geojson['geometry']['type'] != POINT:
                    raise GeoJSONValidationError(
                        'All pourpoints must have a point geometry.',
                    )
                kwargs['point'] = geojson['geometry']
            elif geojson['type'] == GEOM_COLLECTION:
                geoms = geojson['geometries']

                if len(geoms) != 2:
                    raise GeoJSONValidationError(
                        'Multi-geometry pourpoints cannot have more than two geometries',
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
                        'Multi-geometry pourpoints must have one (Mutli)Polygon geometry',
                    )
            else:
                raise GeoJSONValidationError(
                    f"Incompatible type '{geojson['type']}'",
                )

            kwargs['awdb_id'] = geojson['id']
            kwargs['name'] = geojson['properties'].get(
                'nwccname', geojson['properties']['name']
            )
            kwargs['source'] = geojson['properties']['source']
        except KeyError as e:
            raise GeoJSONValidationError(
                'Pourpoint missing required property',
            ) from e

        return cls(**kwargs)

    def insert_sql(self, allow_update=False):
        fields = ['awdb_id', 'name', 'source', 'point']
        values = ['%s', '%s', '%s', 'ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)']
        params = [self.awdb_id, self.name, self.source, json.dumps(self.point)]

        if self.polygon:
            fields.append('polygon')
            values.append('ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)')
            params.append(json.dumps(self.polygon))

        sql = f'insert into {TABLE} ({join(fields)}) values ({join(values)})'

        if allow_update:
            updates = fields[1:]
            excludes = [f'EXCLUDED.{field}' for field in updates]
            sql += f' on conflict (awdb_id) do update set ({join(updates)}) = ({join(excludes)})'

        return sql, params


class Command(BaseCommand):
    help = """
 Load a BAGIS geojson-format pourpoint into the database.
 Simply provide the path to a pourpoint geojson file.

 Also allows updating an existing pourpoint with the update option.
 """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            'pourpoint_geojson',
            action=FullPaths,
            type=is_file,
            help='Path to a BAGIS pourpoint geojson file.',
        )
        parser.add_argument(
            '-u',
            '--update',
            action='store_true',
            default=False,
            help=(
                'Allow updates to a existing pourpoint. '
                'Default behavior will error on conflict.'
            ),
        )
        parser.add_argument(
            '-d',
            '--dry-run',
            action='store_true',
            default=False,
            help="Don't execute insert, just dump sql command",
        )

    def handle(self, *args, **options):
        pourpoint = self.load_pourpoint_geojson(options['pourpoint_geojson'])

        print(f"Inserting pourpoint into database '{pourpoint.awdb_id}'")

        sql, params = pourpoint.insert_sql(allow_update=options['update'])

        if options['dry_run']:
            print(f'SQL: {sql}')
            print(f'PARAMS: {params}')
            return

        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    @staticmethod
    def load_pourpoint_geojson(geojson_file):
        try:
            with open(geojson_file) as f:
                geojson = json.load(f)
        except json.decoder.JSONDecodeError as e:
            raise GeoJSONValidationError(
                'Failed to parse pourpoint json',
            ) from e

        return Pourpoint.from_geojson(geojson)
