from __future__ import print_function

import json

from django.db import connection
from django.http import HttpResponse


def list_tiles(request):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)
    with connection.cursor() as cursor:
        cursor.execute("SELECT date FROM snodas")
        dates = [str(date[0]) for date in cursor.fetchall()]

    return HttpResponse(json.dumps(dates), content_type='application/json')


