import os

from psycopg2 import sql

from django.db import connection
from django.http import HttpResponse
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.db.backends.postgis.pgraster import from_pgraster

from .settings import MEDIA_ROOT


def get_raster_date_range(request, pourpoint_id, variable,
                          start_date, end_date, email):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    pp_query = '''SELECT
  name
FROM
  pourpoint.pourpoint
WHERE
  pourpoint_id = %s'''

    raster_query = '''SELECT
  t.*
FROM
  snodas.raster as r
LATERAL
  ST_Intersection(
    (select polygon from pourpoint.pourpoint where pourpoint_id = {}),
    r.{}
  ) as t
WHERE
  {}::daterange @> date
ORDER BY
  date'''

    daterange = '[{}, {}]'.format(start_date, end_date)
    raster_query = sql.SQL(raster_query).format(
        sql.Literal(pourpoint_id),
        sql.Literal(variable),
        sql.Literal(daterange),
    )

    with connection.cursor() as cursor:
        cursor.execute(pp_query, [pourpoint_id])
        pp = cursor.fetchone()

        if not pp:
            return HttpResponse(status=404)

        name = '{}_{}_{}-{}.nc'.format(
                "-".join(pp[0].split()),
                variable,
                start_date,
                end_date,
            )
        path = os.path.join(MEDIA_ROOT, 'snodas', 'daily', name)

        if not os.path.isfile(path):
            cursor.execute(raster_query)

            raster_def = None
            for raster in cursor:
                raster = from_pgraster(raster)
                if not raster_def:
                    raster_def = raster
                else:
                    raster_def['bands'].extend(raster['bands'])

            raster_def['driver'] = 'netCDF'
            raster_def['name'] = path
            raster = GDALRaster(raster_def)
