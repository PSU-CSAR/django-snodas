import datetime
import os
import pathlib

from argparse import Namespace

import netCDF4 as nc

from django.conf import settings
from django.contrib.gis.db.backends.postgis.pgraster import from_pgraster
from django.contrib.gis.gdal import GDALRaster
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_snodas.constants import snodas_variables
from psycopg2 import sql

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

PP_QUERY = """SELECT
  name
FROM
  pourpoint.pourpoint
WHERE
  pourpoint_id = %s"""

RASTER_QUERY_DOY = """SELECT
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
  date"""

RASTER_QUERY_DATE_RANGE = """SELECT
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
    AND p.pourpoint_id = {id}
ORDER BY
  date"""


def datetype(date):
    return datetime.date(*map(int, date.split('-')))


class Command(BaseCommand):
    help = """Load a SNODAS rasters into the database.
    Simply provide the path to a SNODAS daily tarfile
    and this command will do the rest."""

    requires_system_checks = []
    can_import_settings = True

    table = 'snodas.raster'
    cols = snodas_variables

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
            '-m',
            '--variable',
            # nargs='+',
            choices=self.cols,
            required=True,
            help='What variable do export.',
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
            '-'.join(pourpoint_name.split()),
            options.variable,
            options.start_year,
            options.doy,
            options.end_year,
            options.doy,
        )
        return os.path.join(settings.MEDIA_ROOT, 'snodas', 'doy', name)

    @staticmethod
    def build_query_date_range(options):
        daterange = f'[{options.start_date}, {options.end_date}]'
        return sql.SQL(RASTER_QUERY_DATE_RANGE).format(
            id=sql.Literal(options.pourpoint_id),
            var=sql.SQL(options.variable),
            daterange=sql.Literal(daterange),
        )

    @staticmethod
    def make_path_date_range(options, pourpoint_name):
        name = '{}_{}_{}-{}.nc'.format(
            '-'.join(pourpoint_name.split()),
            options.variable,
            options.start_date.strftime('%Y%m%d'),
            options.end_date.strftime('%Y%m%d'),
        )
        return os.path.join(settings.MEDIA_ROOT, 'snodas', 'daterange', name)

    def handle(self, *args, **options):
        options = Namespace(**options)

        if options.query_type == DOY_NAME:
            raster_query = self.build_query_doy(options)
            make_path = self.make_path_doy
            # TODO: finish this up for DOY queries
            # self.start_date = datetime.date(year=options.start_year, )
            self.interval = 'year'
        elif options.query_type == DATE_RANGE_NAME:
            raster_query = self.build_query_date_range(options)
            make_path = self.make_path_date_range
            self.start_date = options.start_date
            self.interval = 'day'
        else:
            raise CommandError(
                f'Unrecognized query type: {options.subparser_name}',
            )

        with connection.cursor() as cursor:
            cursor.execute(PP_QUERY, [options.pourpoint_id])
            pp = cursor.fetchone()

            if not pp:
                raise CommandError(f'Pourpoint ID not found: {options.pourpoint_id}')

            self.path = make_path(options, pp[0])

            if os.path.isfile(self.path) and not options.force:
                return self.path

            cursor.execute(raster_query)

            if not cursor:
                raise CommandError('Query returned no raster data.')

            raster_def = None
            for raster in cursor:
                raster = from_pgraster(raster[0])
                if not raster_def:
                    raster_def = raster
                else:
                    raster_def['bands'].extend(raster['bands'])

        # create the directory tree if any components missing
        pathlib.Path(os.path.dirname(self.path)).mkdir(
            parents=True,
            exist_ok=True,
        )

        # TODO: print with high verbosity level
        # for key in raster_def.keys():
        #    if key != 'bands':
        #        print(key, raster_def[key])

        raster = GDALRaster(raster_def)

        dsout = self.create_base_dataset(raster)

        var = dsout.createVariable(
            options.variable,
            GDAL_TO_NETCDF_DATATYPES[raster.bands[0].datatype()],
            (self.interval, 'lat', 'lon'),
            zlib=True,
            complevel=9,
            least_significant_digit=1,
            fill_value=raster.bands[0].nodata_value,
        )
        var.standard_name = options.variable
        var.units = 'acre_feet'
        var.setncattr('grid_mapping', 'spatial_ref')

        for index, band in enumerate(raster.bands):
            var[index] = band.data()

        return self.path

    def create_base_dataset(self, raster):
        rows, coords_y, cols, coords_x = self.extract_cells_from_raster_def(raster)

        dsout = nc.Dataset(self.path, 'w', clobber=True, format=NETCDF_FORMAT)

        dsout.createDimension('lat', rows)
        lat = dsout.createVariable('lat', 'f4', ('lat',))
        lat.standard_name = 'latitude'
        lat.units = 'degrees_north'
        lat.axis = 'Y'
        lat[:] = coords_y

        dsout.createDimension('lon', cols)
        lon = dsout.createVariable('lon', 'f4', ('lon',))
        lon.standard_name = 'longitude'
        lon.units = 'degrees_east'
        lon.axis = 'X'
        lon[:] = coords_x

        dsout.createDimension(self.interval, 0)
        times = dsout.createVariable(self.interval, 'u2', (self.interval,))
        times.standard_name = self.interval
        times.long_name = self.interval
        times.units = self.time_ref
        times.calendar = CALENDAR

        # TODO: change time back to standard start date and
        # generate these values based on the start/end args
        times[:] = range(len(raster.bands))

        crs = dsout.createVariable('spatial_ref', 'i4')
        crs.spatial_ref = raster.srs.wkt

        return dsout

    @staticmethod
    def extract_cells_from_raster_def(raster, center_coords=True):
        rows = raster.height
        cols = raster.width
        origin_x, scale_x, skew_x, origin_y, skew_y, scale_y = raster.geotransform

        if skew_x != 0 or skew_y != 0:
            print(f'Found rotation: skew_x={skew_x}, skew_y={skew_y}')
            raise CommandError('Rotated grids are not currently supported')

        center_offset_x = (scale_x * 0.5) if center_coords else 0
        center_offset_y = (scale_y * 0.5) if center_coords else 0

        coords_x = [origin_x + scale_x * col + center_offset_x for col in range(cols)]
        coords_y = [origin_y + scale_y * row + center_offset_y for row in range(rows)]

        return rows, coords_y, cols, coords_x
