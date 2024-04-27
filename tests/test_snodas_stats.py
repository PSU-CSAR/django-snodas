from datetime import date, datetime
from functools import partial

from django.db import connection
from django.test import TestCase

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

constant_raster_sql = """SELECT ST_AddBand(ST_MakeEmptyRaster(
  6935,
  3351,
  {origin_x},
  {origin_y},
  {scale_x},
  {scale_y},
  {skew_x},
  {skew_y},
  {srid}
), '16BSI'::text, 1000, -9999)""".format(**GEOTRANSFORM)

stripe_function_sql = """CREATE OR REPLACE FUNCTION stripe_callback(
  _value double precision[][][],
  _position integer[][],
  VARIADIC _userargs text[]
)
RETURNS double precision
LANGUAGE plpgsql IMMUTABLE
AS $$
DECLARE
  _remainder integer;
  _axis integer;
BEGIN
  IF _userargs[1] = 'EVEN' THEN
    _remainder := 0;
  ELSIF _userargs[1] = 'ODD' THEN
    _remainder := 1;
  ELSE
    RAISE EXCEPTION 'must supply "EVEN" or "ODD" as first userargs to stripe_callback';
  END IF;

  IF _userargs[2] = 'X' THEN
    _axis := 1;
  ELSIF _userargs[2] = 'Y' THEN
    _axis := 2;
  ELSE
    RAISE EXCEPTION 'must supply "X" or "Y" as second userargs to stripe_callback';
  END IF;

  RETURN CASE
    WHEN _position[1][_axis] % 2 = _remainder THEN
      _value[1][1][1]
    ELSE
      -9999
    END;
END;
$$;"""

striped_raster_sql = """SELECT
ST_MapAlgebra(
  ST_AddBand(
    ST_MakeEmptyRaster(
      6935,
      3351,
      {origin_x},
      {origin_y},
      {scale_x},
      {scale_y},
      {skew_x},
      {skew_y},
      {srid}
    ),
    '16BSI'::text,
    1000,
    -9999
  ),
  1,
  'stripe_callback(double precision[], integer[], text[])'::regprocedure,
  NULL,
  'FIRST',
  NULL,
  0,
  0,
  'ODD',
  'X'
)""".format(**GEOTRANSFORM)

snodas_sql = """INSERT INTO snodas.raster (
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
)"""


pourpoint_sql = """INSERT INTO pourpoint.pourpoint (
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
)""".format(
    o_x=GEOTRANSFORM['origin_x'],
    o_y=GEOTRANSFORM['origin_y'],
    srid=GEOTRANSFORM['srid'],
    M_x=GEOTRANSFORM['origin_x'] + GEOTRANSFORM['scale_x'] * POLY_PIXEL_X,
    m_y=GEOTRANSFORM['origin_y'] + GEOTRANSFORM['scale_y'] * POLY_PIXEL_Y,
)


stats_sql = """SELECT
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
"""


class ConstantSNODASTestCase(TestCase):
    def setUp(self):
        with connection.cursor() as cursor:
            # add a striped raster
            s1 = datetime.now()
            print('Adding a null-striped raster...')
            cursor.execute(stripe_function_sql)
            cursor.execute(striped_raster_sql)
            raster_data = cursor.fetchone()[0]
            cursor.execute(
                snodas_sql,
                [raster_data] * 8 + [datetime.strptime('20180502', '%Y%m%d')],
            )
            print(f'Raster added in {datetime.now()-s1}.')

            # add a constant raster
            s1 = datetime.now()
            print('Adding a constant value raster...')
            cursor.execute(constant_raster_sql)
            raster_data = cursor.fetchone()[0]
            cursor.execute(
                snodas_sql,
                [raster_data] * 8 + [datetime.strptime('20180501', '%Y%m%d')],
            )
            print(f'Raster added in {datetime.now()-s1}.')

            # add a pourpoint geom
            s1 = datetime.now()
            print('Adding a pourpoint geom...')
            cursor.execute(pourpoint_sql)
            print(f'Pourpoint added in {datetime.now()-s1}.')

    def test_check_stats(self):
        expected = {
            'constant': (
                partial(self.assertEqual, first=date(2018, 5, 2)),
                partial(self.assertEqual, first=50.0),
                partial(self.assertEqual, first=1.0),
                partial(self.assertEqual, first=1.0),
                partial(self.assertAlmostEqual, first=0.01, places=3),
                partial(self.assertAlmostEqual, first=0.01, places=3),
                partial(self.assertAlmostEqual, first=0.01, places=3),
                partial(self.assertEqual, first=100.0),
                partial(self.assertEqual, first=100.0),
                partial(self.assertEqual, first=1000.0),
            ),
            'striped': (
                partial(self.assertEqual, first=date(2018, 5, 1)),
                partial(self.assertEqual, first=100.0),
                partial(self.assertEqual, first=1.0),
                partial(self.assertEqual, first=1.0),
                partial(self.assertAlmostEqual, first=0.01, places=3),
                partial(self.assertAlmostEqual, first=0.01, places=3),
                partial(self.assertAlmostEqual, first=0.01, places=3),
                partial(self.assertEqual, first=100.0),
                partial(self.assertEqual, first=100.0),
                partial(self.assertEqual, first=1000.0),
            ),
        }

        with connection.cursor() as cursor:
            cursor.execute(stats_sql)
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 2)

            for idx, field in enumerate(rows[0]):
                expected['constant'][idx](second=field)

            for idx, field in enumerate(rows[1]):
                expected['striped'][idx](second=field)


if __name__ == '__main__':
    print(stripe_function_sql)
    print(striped_raster_sql)
    print(constant_raster_sql)
    print(snodas_sql)
    print(pourpoint_sql)
