import logging

from django.db import connection
from django.http import HttpResponse


logger = logging.getLogger(__name__)


def get_points(request):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    query = '''SELECT jsonb_build_object(
  'type', 'FeatureCollection',
  'features', jsonb_agg(features.feature)
)::text
FROM (
  SELECT jsonb_build_object(
    'type', 'Feature',
    'id', pourpoint_id,
    'geometry', ST_AsGeoJSON(point, 6)::jsonb,
    'properties', to_jsonb(inputs) - 'gid' - 'point'
  ) AS feature
  FROM (
    SELECT
      pourpoint_id,
      name,
      awdb_id,
      source,
      point,
      area_meters
    FROM pourpoint.pourpoint
  ) inputs
) features'''

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchone()

    if not rows:
        return HttpResponse(status=204)

    return HttpResponse(
        rows[0],
        content_type='application/vnd.geo+json',
    )


def get_tile(request, zoom, x, y):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    query = 'SELECT pourpoint.get_tile(%s, %s, %s);'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom],
        )
        tile = cursor.fetchone()

    if not tile:
        return HttpResponse(status=404)

    return HttpResponse(
        bytes(tile[0]),
        content_type='application/vnd.mapbox-vector-tile',
    )
