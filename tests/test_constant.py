from django.test import TestCase

from datetime import datetime

from django.db import connection

POLY_PIXEL_X = 100
POLY_PIXEL_Y = 100
GEOTRANSFORM = {
    'origin_x': -124.733333333329000,
    'origin_y': 52.874999999997797,
    'scale_x': 0.008333333333333,
    'scale_y': -0.008333333333333,
    'skew_x': 0,
    'skew_y': 0,
    'srid': 4326,
}

raster_sql = '''SELECT ST_AddBand(ST_MakeEmptyRaster(
  6935,
  3351,
  {origin_x},
  {origin_y},
  {scale_x},
  {scale_y},
  {skew_x},
  {skew_y},
  {srid}
), '16BSI'::text, 1000, -9999)'''.format(**GEOTRANSFORM)


snodas_sql = '''INSERT INTO snodas.raster (
    swe,
    depth,
    runoff,
    sublimation,
    sublimation_blowing,
    precip_solid,
    precip_liquid,
    average_temp,
    date
) VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s
)'''


pourpoint_sql = '''INSERT INTO pourpoint.pourpoint (
  name,
  awdb_id,
  source,
  point,
  polygon
) VALUES (
  'argh',
  'xx1234',
  'ref',
  ST_GeomFromText('POINT({o_x} {o_y})', {srid}),
  ST_GeomFromText('MULTIPOLYGON((({o_x} {o_y}, {M_x} {o_y}, {M_x} {m_y}, {o_x} {m_y}, {o_x} {o_y})))', {srid})
)'''.format(
    o_x=GEOTRANSFORM['origin_x'],
    o_y=GEOTRANSFORM['origin_y'],
    srid=GEOTRANSFORM['srid'],
    M_x=GEOTRANSFORM['origin_x']+GEOTRANSFORM['scale_x']*POLY_PIXEL_X,
    m_y=GEOTRANSFORM['origin_y']+GEOTRANSFORM['scale_y']*POLY_PIXEL_Y,
)


stats_sql = '''SELECT
    date,
    snowcover,
    depth,
    swe,
    runoff,
    sublimation,
    sublimation_blowing,
    precip_solid,
    precip_liquid,
    average_temp
  FROM pourpoint.statistics
'''


#EXPECTED = (
#    100,


class ConstantSNODASTestCase(TestCase):
    def setUp(self):
        with connection.cursor() as cursor:
	    cursor.execute(pourpoint_sql)
            cursor.execute(raster_sql)
            raster_data = cursor.fetchone()[0]
            for day in range(1, 3):
                cursor.execute(
                    snodas_sql,
                    [raster_data]*8 + [datetime.strptime('201805{0:02d}'.format(day), '%Y%m%d')],
                )


    def test_check_stats(self):
        with connection.cursor() as cursor:
            cursor.execute(stats_sql)
            for row in cursor:
                print row
                #assert row == EXPECTED
