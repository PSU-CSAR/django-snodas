import logging

from datetime import date

from django.db import connection

from snodas import types

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


DateList = list[date]


def list_dates() -> DateList:
    with connection.cursor() as cursor:
        cursor.execute('SELECT date FROM snodas.raster ORDER BY date DESC')
        return [date[0] for date in cursor.fetchall()]


def get_tile(
    date: types.Date,
    zoom: types.Zoom,
    x: int,
    y: int,
) -> bytes:
    query = 'SELECT snodas.tile2png((%s, %s, %s)::tms_tilecoordz, %s::date, true)'

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            [x, y, zoom, date],
        )
        row = cursor.fetchone()

    png: bytes = EMPTY_PNG
    if row and row[0]:
        png = row[0]

    return png
