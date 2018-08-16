import json
import logging

from django.db import connection
from django.http import HttpResponse


logger = logging.getLogger(__name__)


def list_dates(request):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    with connection.cursor() as cursor:
        cursor.execute('SELECT date FROM snodas.raster')
        dates = [str(date[0]) for date in cursor.fetchall()]

    return HttpResponse(json.dumps(dates), content_type='application/json')


def get_tile(request, year, month, day, zoom, x, y, format):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    # TODO: actually handle jpeg format tiles
    if format == 'jpg':
        format = 'jpeg'

    # TODO: ability to pass options into the output raster creation
    # e.g., compression or quality settings
    options = "ARRAY['']"

    # TODO: option for resample true/false (currently always false)
    query = 'SELECT snodas.tile2png((%s, %s, %s)::tms_tilecoordz, %s::date, false)'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom, '{}-{}-{}'.format(year, month, day)],
        )
        row = cursor.fetchone()

    if not row or not row[0]:
        return HttpResponse(status=404)

    return HttpResponse(bytes(row[0]), content_type='application/{}'.format(format.lower))
