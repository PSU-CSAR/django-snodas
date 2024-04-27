import os
import pathlib
import datetime

import netCDF4 as nc

from argparse import Namespace
from psycopg2 import sql

from django.db import connection
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.db.backends.postgis.pgraster import from_pgraster


# TODO: use an "atomic replace" to the dest path from an intermediate temp file
# to handle a situation where this is killed before writing the file can finish

# TODO: metadata about creation, e.g. version info and whatever

NETCDF_FORMAT = 'NETCDF4'

GDAL_TO_NETCDF_DATATYPES = {
    # 0: GDT_Unknown and cannot map
    1: 'u1',  # GDT_Byte
    2: 'u2',  # GDT_UInt16
    3: 'i2',  # GDT_Int16
    4: 'u4',  # GDT_UInt32
    5: 'i4',  # GDT_Int32
    6: 'f4',  # GDT_Float32
    7: 'f8',  # GDT_Float64
    # 8: GDT_CInt16, currently unsupported by netCDF
    # 9: GDT_CInt32, currently unsupported by netCDF
    # 10: GDT_CFloat32, currently unsupported by netCDF
    # 11: GDT_CFloat64, currently unsupported by netCDF
}

TIME_REF = '{}s since {} 00:00:00'
CALENDAR = 'standard'

DATE_RANGE_NAME = 'date-range'
DOY_NAME = 'doy'

PP_QUERY = '''SELECT
  p.name,
  ST_Georeference(r.rast) as georef,
  (SELECT * FROM spatial_ref_sys WHERE srid = ST_SRID(r.rast)) as wkt,
  ST_BandNoDataValue(r.rast) as nodata,
FROM
  pourpoint.pourpoint as p
JOIN
  pourpoint.rasterized as r
USING
  (pourpoint_id)
WHERE
  p.pourpoint_id = %s
    AND r.valid_dates @> now()'''

RASTER_QUERY_DOY = '''SELECT
  t
FROM
  snodas.raster as r,
  pourpoint.pourpoint as p,
LATERAL
  ST_Clip(
    r.{var},
    p.polygon,
    true
  ) as t
WHERE
  {daterange}::daterange @> r.date
    AND date_part('month', r.date) = {month}
    AND date_part('day', r.date) = {day}
    AND p.pourpoint_id = {id}
ORDER BY
  date'''

RASTER_QUERY_DATE_RANGE = '''SELECT
  s.date,
  ST_AsBinary(ST_MapAlgebra(s.swe, p.rast, '[rast1]', NULL, 'SECOND', 0, 'NULL')) as swe,
  ST_AsBinary(ST_MapAlgebra(s.depth, p.rast, '[rast1]', NULL, 'SECOND', 0, 'NULL')) as depth,
  ST_AsBinary(ST_MapAlgebra(s.runoff, p.rast, '[rast1]', NULL, 'SECOND', 0, 'NULL')) as runoff,
  ST_AsBinary(ST_MapAlgebra(s.sublimation, p.rast, '[rast1]', NULL, 'SECOND', 0, 'NULL')) as sublimation,
  ST_AsBinary(ST_MapAlgebra(s.sublimation_blowing, p.rast, '[rast1]', SECOND, 'FIRST', 0, 'NULL')) as sublimation_blowing,
  ST_AsBinary(ST_MapAlgebra(s.precip_solid, p.rast, '[rast1]', NULL, 'SECOND', 0, 'NULL')) as precip_solid,
  ST_AsBinary(ST_MapAlgebra(s.precip_liquid, p.rast, '[rast1]', NULL, 'SECOND', 0, 'NULL')) as precip_liquid,
  ST_AsBinary(ST_MapAlgebra(s.average_temp, p.rast, '[rast1]', NULL, 'SECOND', 0, 'NULL')) as average_temp
FROM
  snodas.raster as s,
  pourpoint.rasterized as p
WHERE
  {daterange}::daterange @> s.date
    AND p.pourpoint_id = {id}
    AND p.valid_dates @> s.date
ORDER BY
  s.date'''


def datetype(date):
    return datetime.date(*map(int, date.split('-')))


class Command(BaseCommand):
    help = """Load a SNODAS rasters into the database.
    Simply provide the path to a SNODAS daily tarfile
    and this command will do the rest."""

    requires_system_checks = []
    can_import_settings = True

    table = 'snodas.raster'
    cols = [
        'swe',
        'depth',
        'runoff',
        'sublimation',
        'sublimation_blowing',
        'precip_solid',
        'precip_liquid',
        'average_temp',
        'date',
    ]

    @property
    def time_ref(self):
        try:
            return TIME_REF.format(self.interval, self.start_date)
        except AttributeError:
            raise CommandError(
                'Cannot access time_ref until interval and start date are set',
            )

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-i',
            '--pourpoint_id',
            type=int,
            required=True,
            help='ID of the pourpoint to export',
        )
        parser.add_argument(
            '-F',
            '--force',
            action='store_true',
            default=False,
            help='Force creation of raster even if file already exists',
        )
        subparsers = parser.add_subparsers(dest='query_type')
        date_range = subparsers.add_parser(
            DATE_RANGE_NAME,
            help='Query a consequtive date range',
        )
        date_range.add_argument(
            '-s',
            '--start-date',
            type=datetype,
            required=True,
            help='Start date of query. Format YYYY-MM-DD',
        )
        date_range.add_argument(
            '-e',
            '--end-date',
            type=datetype,
            required=True,
            help='End date of query. Format YYYY-MM-DD',
        )
        single_date = subparsers.add_parser(
            DOY_NAME,
            help='Query a single date over a range of years',
        )
        single_date.add_argument(
            '-s',
            '--start-year',
            type=int,
            required=True,
            help='Start water year of query',
        )
        single_date.add_argument(
            '-e',
            '--end-year',
            type=int,
            required=True,
            help='End water year of query',
        )
        single_date.add_argument(
            '-d',
            '--doy',
            type=int,
            required=True,
            help='Water year DOY for query',
        )

    @staticmethod
    def build_query_doy(options):
        raise NotImplementedError("Haven't gotten to this one yet, sorry!")

    @staticmethod
    def make_path_doy(options, pourpoint_name):
        name = '{}_{}_{}{}-{}{}.nc'.format(
            "-".join(pourpoint_name.split()),
            options.variable,
            options.start_year,
            options.doy,
            options.end_year,
            options.doy,
        )
        return os.path.join(settings.MEDIA_ROOT, 'snodas', 'doy', name)

    @staticmethod
    def build_query_date_range(options):
        daterange = '[{}, {}]'.format(options.start_date, options.end_date)
        return sql.SQL(RASTER_QUERY_DATE_RANGE).format(
            id=sql.Literal(options.pourpoint_id),
            var=sql.SQL(options.variable),
            daterange=sql.Literal(daterange),
        )

    @staticmethod
    def make_path_date_range(options, pourpoint_name):
        name = '{}_{}_{}-{}.nc'.format(
            "-".join(pourpoint_name.split()),
            options.variable,
            options.start_date.strftime("%Y%m%d"),
            options.end_date.strftime("%Y%m%d"),
        )
        return os.path.join(settings.MEDIA_ROOT, 'snodas', 'daterange', name)

    def handle(self, *args, **options):
        options = Namespace(**options)

        if options.query_type == DOY_NAME:
            raster_query = self.build_query_doy(options)
            make_path = self.make_path_doy
            # TODO: finish this up for DOY queries
            #self.start_date = datetime.date(year=options.start_year, )
            self.interval = 'year'
        elif options.query_type == DATE_RANGE_NAME:
            raster_query = self.build_query_date_range(options)
            make_path = self.make_path_date_range
            self.start_date = options.start_date
            self.interval = 'day'
        else:
            raise CommandError(
                'Unrecognized query type: {}'.format(options.subparser_name),
            )

        with connection.cursor() as cursor:
            cursor.execute(PP_QUERY, [options.pourpoint_id])
            pp = cursor.fetchone()

            if not pp:
                raise CommandError('Pourpoint ID not found: {}'.format(
                    options.pourpoint_id,
                ))

            # TODO: override init and set values of all this crap I'm storing in the class
            self.path = make_path(options, pp[0])
            geotransform, wkt, nodata = pp[1], pp[2], pp[3]

            if os.path.isfile(self.path) and not options.force:
                return self.path

            cursor.execute(raster_query)

            if not cursor:
                raise CommandError('Query returned no raster data.')

            pathlib.Path(os.path.dirname(self.path)).mkdir(
                parents=True, exist_ok=True,
            )

            with nc.Dataset(
                self.path, 'w', clobber=True, format=NETCDF_FORMAT,
            ) as ds:
                ds = self._build_netcdf(ds, geotransform, wkt, nodata, cursor)

            raster_def = None
            for raster in cursor:
                raster = from_pgraster(raster[0])
                if not raster_def:
                    raster_def = raster
                else:
                    raster_def['bands'].extend(raster['bands'])

        # create the directory tree if any components missing


        # TODO: print with high verbosity level
        #for key in raster_def.keys():
        #    if key != 'bands':
        #        print(key, raster_def[key])

        raster = GDALRaster(raster_def)

        dsout =



        for index, band in enumerate(raster.bands):
            var[index] = band.data()

        return self.path

    def _build_netcdf(self, ds, geotransform, wkt, nodata, cursor):
        rows, coords_y, cols, coords_x = \
            self.extract_cells_from_raster_def(geotransform)

        ds.createDimension('lat', rows)
        lat = ds.createVariable('lat', 'f4', ('lat',))
        lat.standard_name = 'latitude'
        lat.units = 'degrees_north'
        lat.axis = "Y"
        lat[:] = coords_y

        ds.createDimension('lon', cols)
        lon = ds.createVariable('lon', 'f4', ('lon',))
        lon.standard_name = 'longitude'
        lon.units = 'degrees_east'
        lon.axis = "X"
        lon[:] = coords_x

        crs = ds.createVariable('spatial_ref', 'i4')
        crs.spatial_ref = wkt

        ds.createDimension(self.interval, 0)
        times = ds.createVariable(self.interval, 'u2', (self.interval,))
        times.standard_name = self.interval
        times.long_name = self.interval
        times.units = self.time_ref
        times.calendar = CALENDAR

        def create_variable(name, longname, units):
            var = ds.createVariable(
                name,
                'i2',
                (self.interval, 'lat', 'lon'),
                zlib=True,
                complevel=9,
                least_significant_digit=1,
                fill_value=nodata,
            )
            var.standard_name = longname
            var.units = units
            var.setncattr('grid_mapping', 'spatial_ref')
            return var

        swe = create_variable('swe', 'snow_water_equivalent', 'acre_feet')
        depth = create_variable('depth', 'snow_depth', 'm')
        runoff = create_variable('runoff', 'runoff_at_snowpack_base', 'acre_feet')
        sublimation = create_variable('sublimation', 'sublimation', 'acre_feet')
        sublimation_blowing = create_variable('sublimation_blowing', 'sublimation_blowing', 'acre_feet')
        precip_solid = create_variable('precip_solid', 'solid_precipitation', 'acre_feet')
        precip_liquid = create_variable('precip_liquid', 'liquid_precipitation', 'acre_feet')
        average_temp = create_variable('average_temp', 'snowpack_average_temperature', 'k')

        times = set()
        for record in cursor:
            time_index = nc.date2num(record[0], units=self.time_ref, calendar=CALENDAR)
            times.add(time_index)
            swe[time_index] = self.wkb_to_numpy(record[1])
            depth[time_index] = self.wkb_to_numpy(record[2])
            runoff[time_index] = self.wkb_to_numpy(record[3])
            sublimation[time_index] = self.wkb_to_numpy(record[4])
            sublimation_blowing[time_index] = self.wkb_to_numpy(record[5])
            precip_solid[time_index] = self.wkb_to_numpy(record[6])
            precip_liquid[time_index] = self.wkb_to_numpy(record[7])
            average_temp[time_index] = self.wkb_to_numpy(record[8])

        # TODO: change time back to standard start date and
        # generate these values based on the start/end args
        times[:] = sorted(times)

    @staticmethod
    def wkb_to_numpy(wkb):
        import struct
        import numpy as np
        import cv2

        # Function to decypher the WKB header
        def wkbHeader(raw):
            # See http://trac.osgeo.org/postgis/browser/trunk/raster/doc/RFC2-WellKnownBinaryFormat

            header = {}

            header['endianess'] = struct.unpack('B', raw[0])[0]
            header['version'] = struct.unpack('H', raw[1:3])[0]
            header['nbands'] = struct.unpack('H', raw[3:5])[0]
            header['scaleX'] = struct.unpack('d', raw[5:13])[0]
            header['scaleY'] = struct.unpack('d', raw[13:21])[0]
            header['ipX'] = struct.unpack('d', raw[21:29])[0]
            header['ipY'] = struct.unpack('d', raw[29:37])[0]
            header['skewX'] = struct.unpack('d', raw[37:45])[0]
            header['skewY'] = struct.unpack('d', raw[45:53])[0]
            header['srid'] = struct.unpack('i', raw[53:57])[0]
            header['width'] = struct.unpack('H', raw[57:59])[0]
            header['height'] = struct.unpack('H', raw[59:61])[0]

            return header

        # Function to decypher the WKB raster data
        def wkbImage(raw):
            h = wkbHeader(raw)
            img = [] # array to store image bands
            offset = 61 # header raw length in bytes
            for i in range(h['nbands']):
                # Determine pixtype for this band
                pixtype = struct.unpack('B', raw[offset])[0]>>4
                # For now, we only handle unsigned byte
                if pixtype == 4:
                    band = np.frombuffer(raw, dtype='uint8', count=h['width']*h['height'], offset=offset+1)
                    img.append(np.reshape(band, ((h['height'], h['width']))))
                    offset = offset + 2 + h['width']*h['height']
                # to do: handle other data types

            return cv2.merge(tuple(img))

    @staticmethod
    def _extract_cells_from_geotransform(geotransform, center_coords=True):
        rows = raster.height
        cols = raster.width
        origin_x, scale_x, skew_x, origin_y, skew_y, scale_y = geotransform

        if skew_x != 0 or skew_y != 0:
            print('Found rotation: skew_x={}, skew_y={}'.format(skew_x, skew_y))
            raise CommandError('Rotated grids are not currently supported')

        center_offset_x = (scale_x * 0.5) if center_coords else 0
        center_offset_y = (scale_y * 0.5) if center_coords else 0

        coords_x = [origin_x + scale_x * col + center_offset_x for col in range(cols)]
        coords_y = [origin_y + scale_y * row + center_offset_y for row in range(rows)]

        return rows, coords_y, cols, coords_x
