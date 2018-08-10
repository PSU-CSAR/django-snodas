from __future__ import print_function

from django.db import connection
from django.http import HttpResponse


def get_tile(request, zoom, x, y):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    query = 'SELECT get_pourpoint_tile(%s, %s, %s);'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom],
        )
        tile = cursor.fetchone()

    if not tile:
        return HttpResponse(status=404)

    return HttpResponse(tile[0], content_type='application/vnd.mapbox-vector-tile')
