import logging
from typing import assert_never

from django.db import connection
from django.http import HttpResponse, Http404

from snodas import types


logger = logging.getLogger(__name__)


def get_points() -> types.PourPoints:
    query = '''
        SELECT jsonb_build_object(
            'type', 'Feature',
            'id', pourpoint_id,
            'geometry', ST_AsGeoJSON(point, 6)::jsonb,
            'properties', to_jsonb(inputs) - 'gid' - 'point' - 'pourpoint_id'
        ) AS feature
        FROM (
            SELECT
                pourpoint_id,
                name,
                awdb_id as station_triplet,
                point,
                area_meters
            FROM pourpoint.pourpoint
        ) inputs
    '''

    with connection.cursor() as cursor:
        cursor.execute(query)
        return types.PourPoints(
            features=[
                types.PourPoint.model_validate_json(feat[0])
                for feat in cursor.fetchall()
            ],
        )


def get_point(pourpoint_ref: int | str) -> types.PourPoint:
    match pourpoint_ref:
        case int():
            query = '''
                SELECT jsonb_build_object(
                    'type', 'Feature',
                    'id', pourpoint_id,
                    'geometry', ST_AsGeoJSON(point, 6)::jsonb,
                    'properties', to_jsonb(inputs) - 'gid' - 'point' - 'pourpoint_id'
                ) AS feature
                FROM (
                    SELECT
                        pourpoint_id,
                        name,
                        awdb_id as station_triplet,
                        point,
                        area_meters
                    FROM pourpoint.pourpoint
                    WHERE pourpoint_id = %s
                ) inputs
            '''
        case str():
            query = '''
                SELECT jsonb_build_object(
                    'type', 'Feature',
                    'id', pourpoint_id,
                    'geometry', ST_AsGeoJSON(point, 6)::jsonb,
                    'properties', to_jsonb(inputs) - 'gid' - 'point' - 'pourpoint_id'
                ) AS feature
                FROM (
                    SELECT
                        pourpoint_id,
                        name,
                        awdb_id as station_triplet,
                        point,
                        area_meters
                    FROM pourpoint.pourpoint
                    WHERE awdb_id = %s
                ) inputs
            '''
        case _ as unreachable:
            assert_never(unreachable)

    with connection.cursor() as cursor:
        cursor.execute(query, [pourpoint_ref])
        row = cursor.fetchone()

        if not row:
            raise Http404()

        return types.PourPoint.model_validate_json(row[0])


def get_tile(zoom: types.Zoom, x: int, y: int) -> bytes:
    query: str = 'SELECT pourpoint.get_tile(%s, %s, %s);'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom],
        )
        tile = cursor.fetchone()

    if not (tile and tile[0]):
        raise Http404()

    return bytes(tile[0])
