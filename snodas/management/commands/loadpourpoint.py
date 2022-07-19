import json

from django.core.management.base import BaseCommand
from django.db import connection

from ...exceptions import GeoJSONValidationError

from ..utils import FullPaths, is_file


TABLE = 'pourpoint.pourpoint'


class Pourpoint:
    def __init__(self, awdb_id, name, source, point, polygon=None):
        self.awdb_id
        self.name
        self.source
        self.point
        self.polygon

    @classmethod
    def from_geojson(cls, geojson):
        args = {}
        try:
            if geojson['type'] == 'Feature':
                if geojson['geometry']['type'] != 'Point':
                    raise GeoJSONValidationError(
                        'All pourpoints must have a point geometry.',
                    )
                args['point'] = geojson['geometry']
            elif geojson['type'] == 'GeometryCollection':
                geoms = geojson['geometries']

                if len(geoms) != 2:
                    raise GeoJSONValidationError(
                        'Multi-geometry pourpoints cannot have more than two geometries',
                    )

                if geoms[0]['type'] == 'Point':
                    args['point'] = geoms[0]
                elif geoms[1]['type'] == 'Point':
                    args['point'] = geoms[1]
                else:
                    raise GeoJSONValidationError(
                        'All pourpoints must have a point geometry.',
                    )

                if geoms[0]['type'] in ['Polygon', 'MutliPolygon']:
                    args['polygon'] = geoms[0]
                elif geoms[1]['type'] in ['Polygon', 'MutliPolygon']:
                    args['polygon'] = geoms[1]
                else:
                    raise GeoJSONValidationError(
                        'Multi-geometry pourpoints must have one (Mutli)Polygon geometry',
                    )
            else:
                raise GeoJSONValidationError(
                    f"Incompatible type '{geojson['type']}'",
                )

            args['awdb_id'] = geojson['id']
            args['name'] = geojson['properties']['name']
            args['source'] = geojson['properties']['source']
        except KeyError as e:
            raise GeoJSONValidationError(
                'Pourpoint missing required property',
            ) from e

        return cls(**args)

    def insert(self, cursor):
        fields = '(awdb_id, name, source, point'
        values = '(%s, %s, %s, ST_GeomFromGeoJSON(%s)'
        params = [self.awdb_id, self.name, self.source, self.point]

        if self.polygon:
            fields += ', polygon'
            values += ', ST_Transform(ST_GeomFromGeoJSON(%s), 5070)'
            params.append(self.polygon)

        fields += ')'
        values += ')'
        sql = f'insert into {TABLE} {fields} values {values}'

        cursor.execute(sql, params)


class Command(BaseCommand):
    help = (
        'Load one or more BAGIS geojson-format pourpoints into the database. '
        'Simply provide the path to a pourpoint geojson file'
    )

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            'pourpoint_geojson',
            action=FullPaths,
            type=is_file,
            help='Path to a BAGIS pourpoint geojson file.',
        )

    def handle(self, *args, **options):
        pourpoint = self.load_pourpoint_geojson(options['pourpoint_geojson'])

        print(f"Inserting pourpoint into database '{pourpoint.id}'")
        with connection.cursor() as cursor:
            pourpoint.insert(cursor)

    @staticmethod
    def load_pourpoint_geojson(geojson_file):
        try:
            with open(geojson_file) as f:
                geojson = json.load(f)
        except json.decoder.JSONDecodeError as e:
            raise GeoJSONValidationError(
                'Failed to parse pourpoint json'
            ) from e

        return Pourpoint.from_geojson(geojson)
