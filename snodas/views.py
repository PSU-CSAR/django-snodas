from __future__ import print_function

import json

from django.db import connection
from django.http import HttpResponse

from .exceptions import GeoJSONValidationError


def list_tiles(request):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)
    with connection.cursor() as cursor:
        cursor.execute("SELECT date FROM snodas")
        dates = [str(date[0]) for date in cursor.fetchall()]

    return HttpResponse(json.dumps(dates), content_type='application/json')


def get_tile(request, date, zoom, x, y, format):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    # TODO: actually handle jpeg format tiles
    if format == 'jpg':
        format = 'jpeg'

    # TODO: ability to pass options into the output raster creation
    # e.g., compression or quality settings
    options = "ARRAY['']"

    # TODO: option for resample true/false (currently always false)
    query = 'SELECT snodas2png((%s, %s, %s)::tms_tilecoordz, %s::date, false)'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom, date],
        )
        row = cursor.fetchone()

    if not row:
        return HttpResponse(status=404)

    return HttpResponse(row[0], content_type='application/{}'.format(format.lower))


def get_pourpoint_tile(request, zoom, x, y):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

#    tolerance = 100

#    query_points = \
#'''SELECT (
#  SELECT ST_AsMVT(points)
#  FROM (
#    SELECT
#      id,
#      name,
#      source,
#      ST_AsMVTGeom(
#        geom,
#        tile,
#        4096,
#        100,
#        true
#      ) AS geom
#      FROM (
#        SELECT
#          pourpoint.id as id,
#          pourpoint.name as name,
#          pourpoint.source as source,
#          st_transform(pourpoint.point, 3857) as geom,
#          tile.extent as tile
#        FROM pourpoint, (select (%s, %s, %s)::tms_tilecoordz::geometry as extent) as tile
#        WHERE
#          st_transform(tile.extent, 4326) && pourpoint.point
#      ) as point
#  ) AS points) ||
#  (SELECT ST_AsMVT(polygons)
#  FROM (
#    SELECT
#      id,
#      name,
#      source,
#      ST_AsMVTGeom(
#        geom,
#        tile,
#        4096,
#        100,
#        true
#      ) AS geom
#      FROM (
#        SELECT
#          pourpoint.id as id,
#          pourpoint.name as name,
#          pourpoint.source as source,
#          st_transform(st_simplifypreservetopology(pourpoint.polygon_simple, %s / (2^%s * 4096)), 3857) as geom,
#          tile.extent as tile
#        FROM pourpoint, (select (%s, %s, %s)::tms_tilecoordz::geometry as extent) as tile
#        WHERE
#          st_transform(tile.extent, 4326) && pourpoint.polygon_simple AND
#          pourpoint.polygon_simple is not Null
#      ) as poly
#  ) AS polygons)'''

    query = 'SELECT get_pourpoint_tile(%s, %s, %s);'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom],
        )
        tile = cursor.fetchone()
       # cursor.execute(
       #     query_polygons,
       #     [tolerance, zoom, x, y, zoom],
       # )
       # polygons = cursor.fetchone()

#    if points and polygons:
#        tile = points[0] + polygons[0]
#    elif not points:
#        tile = polygons[0]
#    elif not polygons:
#        tile = points[0]
#    else:
    if not tile:
        return HttpResponse(status=404)

    return HttpResponse(tile[0], content_type='application/vnd.mapbox-vector-tile')


def get_file(request, zoom, x, y):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    try:
        with open('./{zoom}_{x}_{y}.mvt'.format(zoom=zoom, x=x, y=y)) as t:
            tile = t.read()
    except IOError:
        return HttpResponse(status=404)

    return HttpResponse(tile, content_type='application/vnd.mapbox-vector-tile')


def validate_geojson(geom):
    try:
        if geom['type'] == 'FeatureCollection':
            if len(geom['features']) == 1:
                geom = geom['features']['geometry']
            else:
                raise GeoJSONValidationError(
                    'GeoJSON must contain exactly 1 valid geometry',
                )
        elif geom['type'] == 'Feature':
            geom = geom['geometry']
    except KeyError:
        raise GeoJSONValidationError(
            'GeoJSON appears to be invalid',
        )
    return geom


def get_stats_date(request, start_year, end_year, month, day):
    if request.method != 'POST':
        return HttpResponse(reason="Not allowed", status=405)

    if start_year > end_year:
        return HttpResponse(
            reason='Start year cannot be after end year: {} > {}'.format(
                start_year,
                end_year,
            ),
            status=400,
        )

    if month not in range(1, 13):
        return HttpResponse(
            reason='Month {} is not a valid value'.format(month),
            status=400,
        )

    if day not in range(1, (29 if month == 2 else 31 - (month - 1) % 7 % 2)):
        return HttpResponse(
            reason='Invalid day {} for month {}'.format(day, month),
            status=400,
        )

    try:
        geom = validate_geojson(json.loads(request.body))
    except GeoJSONValidationError as e:
        return HttpResponse(reason=e.args[0], status=400)

    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT * FROM snodas_query(%s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))',
            [start_year, end_year, month, day, geom],
        )
        row = cursor.fetchone()

    if not row:
        return HttpResponse(status=404)

    return HttpResponse(row[0], content_type='application/json')


def get_stats_doy(request, start_year, end_year, doy):
    if request.method != 'POST':
        return HttpResponse(reason="Not allowed", status=405)

    if start_year > end_year:
        return HttpResponse(
            reason='Start year cannot be after end year: {} > {}'.format(
                start_year,
                end_year,
            ),
            status=400,
        )

    if doy not in xrange(1, 367):
        return HttpResponse(
            reason='Day-of-year {} is not a valid value'.format(doy),
            status=400,
        )

    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT * FROM snodas_query(%s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))',
            [start_year, end_year, doy, geom],
        )
        row = cursor.fetchone()

    if not row:
        return HttpResponse(status=404)

    return HttpResponse(row[0], content_type='application/json')
