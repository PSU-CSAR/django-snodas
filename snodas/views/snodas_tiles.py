import json
import logging

from django.db import connection
from django.http import HttpResponse


logger = logging.getLogger(__name__)


EMPTY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08'
    b'\x00\x00\x00\x00y\x19\xf7\xba\x00\x00\x00\x02tRNS\x00\x00v\x93\xcd8\x00'
    b'\x00\x00TIDATx\x9c\xed\xc1\x01\x01\x00\x00\x00\x80\x90\xfe\xaf\xee\x08'
    b'\n\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x01\x0f\x00\x01M\xf6\xca'
    b'\x06\x00\x00\x00\x00IEND\xaeB`\x82'
)


def list_dates(request):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    with connection.cursor() as cursor:
        cursor.execute('SELECT date FROM snodas.raster ORDER BY date DESC')
        dates = [str(date[0]) for date in cursor.fetchall()]

    return HttpResponse(json.dumps(dates), content_type='application/json')


# TODO: clean this up because it did not help anything
def date_params(request):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    query = '''WITH start_end as (
  SELECT
    MIN(date) as start_date,
    MAX(date) as end_date
  FROM
    snodas.raster
)
SELECT row_to_json(t)::text
FROM (
  SELECT
    (SELECT start_end.start_date::text as start_date FROM start_end),
    (SELECT start_end.end_date::text as end_date FROM start_end),
    json_agg(missing::date::text) as missing
  FROM
    generate_series(
      (SELECT start_date FROM start_end),
      (SELECT end_date FROM start_end),
      interval '1 day'
    ) AS missing
  WHERE
    missing NOT IN (SELECT date FROM snodas.raster)
) as t'''

    with connection.cursor() as cursor:
        cursor.execute(query)
        dates = cursor.fetchone()

    return HttpResponse(dates, content_type='application/json')


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
    query = \
        'SELECT snodas.tile2png((%s, %s, %s)::tms_tilecoordz, %s::date, true)'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom, '{}-{}-{}'.format(year, month, day)],
        )
        row = cursor.fetchone()

    if not row or not row[0]:
        png = EMPTY_PNG
    else:
        png = row[0]

    return HttpResponse(
        bytes(png),
        content_type='application/{}'.format(format.lower),
    )
