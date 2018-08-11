import os
import re
import gzip
import glob
import tarfile
import shutil

from datetime import datetime

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.db.backends.postgis.pgraster import to_pgraster

from ...exceptions import SNODASError
from ...utils.filesystem import tempdirectory

from ..utils import to_namedtuple, FullPaths, is_file


def parse_filename(path):
    '''Parse out the file info from a provided filename.
    Please refer to the SNODAS naming docs for more information.

    https://nsidc.org/data/g02158#untar_daily_nc'''
    name, ext = os.path.splitext(os.path.basename(path))

    if ext != '.Hdr':
        raise SNODASError('File ext {} is unknown'.format(ext))

    info = re.match(
        (r'(?P<region>[a-z]{2})_'
         r'(?P<model>[a-z]{3})'
         r'(?P<datatype>v\d)'
         r'(?P<product_code>\d{4})'
         r'(?P<scaled>S?)'
         r'(?P<vcode>[a-zA-Z]{2}[\d_]{2})'
         r'(?P<timecode>[AT]00[02][14])'
         r'TTNATS'
         r'(?P<date>\d{8})'
         r'(?P<hour>\d{2})'
         r'(?P<interval>H|D)'
         r'(?P<offset>P00[01])'),
        name,
    ).groupdict()

    if not info:
        raise SNODASError('Filename could not be parsed: {}'.format(name))

    info['product_code'] = int(info['product_code'])
    info['date'] = datetime.strptime(info['date'], '%Y%m%d')
    info['name'] = name
    return to_namedtuple(info)


def snodas_type_from_file_info(file_info):
    stypes = {
        1025: 'precip',
        1034: 'swe',
        1036: 'depth',
        1038: 'average_temp',
        1039: 'sublimation_blowing',
        1044: 'runoff',
        1050: 'sublimation',
    }

    stype = stypes[file_info.product_code]

    if stype == 'precip' and file_info.vcode == 'lL00':
        stype = 'precip_liquid'
    elif stype == 'precip' and file_info.vcode == 'lL01':
        stype = 'precip_solid'

    return stype


def extract_snodas_data(snodas_tar):
    rasters = {}
    with tempdirectory() as temp:
        tar = tarfile.open(snodas_tar)
        print('Extracting {}\n\tto temp dir {}'.format(snodas_tar, temp))
        tar.extractall(temp)

        gzipped = glob.glob(os.path.join(temp, '*.gz'))
        for idx, f in enumerate(gzipped, start=1):
            print('Unzipping file {} of {}: {}'.format(idx, len(gzipped), os.path.basename(f)))
            with gzip.open(f, 'rb') as f_in, open(os.path.splitext(f)[0], 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        hdrs = glob.glob(os.path.join(temp, '*.Hdr'))
        for idx, hdr in enumerate(hdrs, start=1):
            print('Importing {} of {}: {}'.format(idx, len(hdrs), os.path.basename(hdr)))
            file_info = parse_filename(hdr)
            rasters[snodas_type_from_file_info(file_info)] = {
                'raster': to_pgraster(GDALRaster(hdr)),
                'info': file_info
            }
    return rasters


def validate_raster_dates(rasters):
    dates = set()
    for key, raster in rasters.items():
        dates.add(raster['info'].date)

    if len(dates) > 1:
        raise SNODASError("SNODAS rasters not all from same date per filenames")

    return dates.pop()


class Command(BaseCommand):
    help = """Load a SNODAS rasters into the database.
    Simply provide the path to a SNODAS daily tarfile
    and this command will do the rest."""

    requires_system_checks = False
    can_import_settings = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            'snodas_tar',
            action=FullPaths,
            type=is_file,
            help='Path to a SNODAS tarfile.',
        )

    def handle(self, *args, **options):
        rasters = extract_snodas_data(options['snodas_tar'])

        date = validate_raster_dates(rasters)

        sql = '''INSERT INTO snodas.raster (
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

        print('Inserting record into database')
        connection.prepare_database()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    [
                        rasters['swe']['raster'],
                        rasters['depth']['raster'],
                        rasters['runoff']['raster'],
                        rasters['sublimation']['raster'],
                        rasters['sublimation_blowing']['raster'],
                        rasters['precip_solid']['raster'],
                        rasters['precip_liquid']['raster'],
                        rasters['average_temp']['raster'],
                        date,
                    ],
                )
        except KeyError as e:
            raise SNODASError('SNODAS data appears incomplete: {}'.format(str(e)))

        print('Processing completed successfully')
