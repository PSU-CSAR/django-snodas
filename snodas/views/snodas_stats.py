import json

from io import BytesIO

from psycopg2 import sql

from django.db import connection
from django.http import HttpResponse

from ..utils.http import stream_file
from ..exceptions import GeoJSONValidationError


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


def raw_stat_query(request, cursor, filename, stat_query):
    flike = BytesIO()
    csvquery = "COPY ({}) TO STDOUT WITH CSV HEADER".format(stat_query.as_string(cursor.connection))
    cursor.copy_expert(csvquery, flike)

    return stream_file(
            flike,
            filename,
            request,
            'text/csv',
        )


def get_raw_statistics_pourpoint(request, query_type, pourpoint_id,
                                 start_date, end_date, name=None):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    pp_query = '''SELECT
  name,
  ST_Y(point::geometry) as lat,
  ST_X(point::geometry) as long
FROM
  pourpoint.pourpoint
WHERE
  pourpoint_id = %s'''

    stat_query = '''SELECT
  date,
  swe,
  depth,
  runoff,
  sublimation,
  sublimation_blowing,
  precip_solid,
  precip_liquid,
  average_temp
FROM
  pourpoint.statistics
WHERE
  pourpoint_id = {} AND
  {}::daterange @> date
ORDER BY
  date'''

    daterange = '[{}, {}]'.format(start_date, end_date)
    stat_query = sql.SQL(stat_query).format(sql.Literal(pourpoint_id), sql.Literal(daterange))

    with connection.cursor() as cursor:
        cursor.execute(pp_query, [pourpoint_id])
        pp = cursor.fetchone()

        if not pp:
            return HttpResponse(status=404)

        if not name:
            name = '{}_{}-{}.csv'.format(
                    "-".join(pp[0].split()),
                    start_date,
                    end_date,
                )

        if query_type == 'point':
            return get_raw_statistics_feature(
                    request,
                    start_date,
                    end_date,
                    lat=pp[1],
                    long=pp[2],
                    name=name,
                )

        return raw_stat_query(request, cursor, name, stat_query)


def get_raw_statistics_feature(request, start_date, end_date, lat, long, name=None):
    if request.method != 'GET' and not all([lat, long]):
        return HttpResponse(reason="Not allowed", status=405)

    stat_query = '''WITH
point AS (SELECT ST_SetSRID(ST_MakePoint({}, {}), 4326) as p)
SELECT
  date,
  ST_Value(s.swe, p, False) as swe,
  ST_Value(s.depth, p, False) as depth,
  ST_Value(s.runoff, p, False) as runoff,
  ST_Value(s.sublimation, p, False) as sublimation,
  ST_Value(s.sublimation_blowing, p, False) as sublimation_blowing,
  ST_Value(s.precip_solid, p, False) as precip_solid,
  ST_Value(s.precip_liquid, p, False) as precip_liquid,
  ST_Value(s.average_temp, p, False) as average_temp
FROM
  snodas.raster as s,
  (SELECT p FROM point) as p
WHERE
  {}::daterange @> s.date'''

    daterange = '[{}, {}]'.format(start_date, end_date)
    stat_query = sql.SQL(stat_query).format(
            sql.Literal(long),
            sql.Literal(lat),
            sql.Literal(daterange),
        )

    with connection.cursor() as cursor:
        if not name:
            name = '{}-{}_{}-{}.csv'.format(
                    lat,
                    long,
                    start_date,
                    end_date,
                )

        return raw_stat_query(request, cursor, name, stat_query)


def get_for_date(request, start_year, end_year, month, day):
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


def get_for_doy(request, start_year, end_year, doy):
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

    if doy not in range(1, 367):
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
