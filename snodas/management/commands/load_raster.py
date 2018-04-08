from __future__ import absolute_import, print_function

import os
import re

from datetime import datetime

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.db.backends.postgis.pgraster import to_pgraster

from ...exceptions import SNODASError

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


class Command(BaseCommand):
    help = """Load a SNODAS SWE raster into the database.
    Simply provide the path to the .Hdr file and thisi command will do the rest."""

    requires_system_checks = False
    can_import_settings = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            'hdr_file',
            action=FullPaths,
            type=is_file,
            help='Path to the .Hdr file.',
        )

    def handle(self, *args, **options):
        path = options['hdr_file']

        file_info = parse_filename(path)

        if not file_info.product_code == 1034:
            raise SNODASError(
                'Product code is not recognized as SWE data: {}'.format(file_info.product_code)
            )

        rast = GDALRaster(path)

        connection.prepare_database()
        with connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO snodas ("date", "rast", "filename") VALUES (%s, %s, %s)',
                [file_info.date, to_pgraster(rast), file_info.name],
            )

