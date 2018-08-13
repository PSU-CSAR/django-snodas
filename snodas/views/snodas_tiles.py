import json

from django.db import connection
from django.http import HttpResponse


def list_dates(request):
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
