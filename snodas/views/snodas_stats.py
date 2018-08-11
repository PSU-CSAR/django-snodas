import json

from django.db import connection
from django.http import HttpResponse

from .exceptions import GeoJSONValidationError


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
