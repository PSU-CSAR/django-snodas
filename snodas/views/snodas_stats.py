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


def get_raw_statistics_pourpoint(request, pourpoint_id, start_date, end_date):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    pp_query = '''SELECT
  name
FROM
  pourpoint.pourpoint
WHERE
  pourpoint_id = %s'''

    stat_query = '''SELECT
  date,
  depth,
  swe,
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

        pp_name = '{}_{}-{}.csv'.format(
            "-".join(pp[0].split()),
            start_date,
            end_date,
        )

        return raw_stat_query(request, cursor, pp_name, stat_query)


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
