import os
import re
import gzip
import glob
import tarfile
import shutil

from io import BytesIO

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.conf import settings

from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.db.backends.postgis.pgraster import to_pgraster

from ...exceptions import SNODASError
from ...utils.filesystem import tempdirectory

from ..utils import to_namedtuple, FullPaths, is_file, is_dir, chain_streams


AVERAGE_TEMP_REQUIRED = True
HDR_EXTS = ('.Hdr', '.txt')


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

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            'snodas_tar',
            action=FullPaths,
            type=is_file,
            help='Path to a SNODAS tarfile.',
        )
        parser.add_argument(
            '-o',
            '--output-dir',
            action=FullPaths,
            type=is_dir,
            help=('Path to a directory in which to retain the expanded files. '
                  'Default is to use a temp directory deleted on exit.'),
        )

    def handle(self, *args, **options):
        if settings.DEBUG:
            raise CommandError(
               'Debug logging can cause problems for loadraster. '
               'Turn off DEBUG before running loadraster.'
            )
        rasters = self.extract_snodas_data(
            options['snodas_tar'],
            outdir=options.get('output_dir', None),
        )
        date = self.validate_raster_dates(rasters)

        try:
            raster_streams = [
                    rasters['swe']['raster'],
                    rasters['depth']['raster'],
                    rasters['runoff']['raster'],
                    rasters['sublimation']['raster'],
                    rasters['sublimation_blowing']['raster'],
                    rasters['precip_solid']['raster'],
                    rasters['precip_liquid']['raster'],
            ]
        except KeyError as e:
            print('ERROR: SNODAS data appears incomplete: {}'.format(str(e)))
            raise

        try:
            raster_streams.append(rasters['average_temp']['raster'])
        except KeyError as e:
            # early data has aerage temp missing,
            # (and also has a funky undocumented grid)
            # but all modern data should have it
            # we have a hard override just for
            # this weird histroical accident
            if AVERAGE_TEMP_REQUIRED:
                print(
                    'ERROR: SNODAS data appears incomplete: {}'.format(str(e))
                )
                raise
            raster_streams.append(BytesIO(b'\N'))

        raster_streams.append(BytesIO(date.encode()))
        ftype = chain_streams(raster_streams, sep=b'\t')

        print('Inserting record into database for date {}'.format(date))
        with connection.cursor() as cursor:
            try:
                cursor.copy_expert(f'copy {self.table} from stdin', ftype)
                del rasters
            except KeyError as e:
                raise SNODASError(
                    'SNODAS data appears incomplete: {}'.format(str(e)),
                )

        print('Processing completed successfully')

    @staticmethod
    def parse_filename(path):
        '''Parse out the file info from a provided filename.
        Please refer to the SNODAS naming docs for more information.

        https://nsidc.org/data/g02158#untar_daily_nc'''
        name, ext = os.path.splitext(os.path.basename(path))

        if ext not in HDR_EXTS:
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
        info['name'] = name
        return to_namedtuple(info)

    @staticmethod
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

    @staticmethod
    def trim_header(hdr):
        '''gdal has a header line length limit of
        256 chars for <2.3.0, or 1024 chars for >=2.3.0,
        but we trim to the smaller size to be safe.'''
        lines = []
        with open(hdr) as f:
            for line in f:
                lines.append(line[:min(len(line), 254)] + '\n')

        with open(hdr, 'w') as f:
            f.writelines(lines)

    def extract_snodas_data(self, snodas_tar, outdir=None):
        rasters = {}
        with tempdirectory() as temp:
            if not outdir:
                outdir = temp
            tar = tarfile.open(snodas_tar)
            print('Extracting {}\n\tto temp dir {}'.format(snodas_tar, temp))
            tar.extractall(temp)

            gzipped = glob.glob(os.path.join(temp, '*.gz'))
            for idx, f in enumerate(gzipped, start=1):
                print(
                    'Unzipping file {} of {}: {}'.format(
                        idx,
                        len(gzipped),
                        os.path.basename(f),
                    ),
                )
                outpath = os.path.join(
                    outdir,
                    os.path.splitext(os.path.basename(f))[0],
                )
                with gzip.open(f, 'rb') as f_in, \
                        open(outpath, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            hdrs = []
            for ext in HDR_EXTS:
                hdrs.extend(glob.glob(os.path.join(outdir, '*{}'.format(ext))))

            for idx, hdr in enumerate(hdrs, start=1):
                print(
                    'Importing {} of {}: {}'.format(
                        idx,
                        len(hdrs),
                        os.path.basename(hdr),
                    ),
                )
                self.trim_header(hdr)
                file_info = self.parse_filename(hdr)
                rasters[self.snodas_type_from_file_info(file_info)] = {
                    'raster': BytesIO(to_pgraster(GDALRaster(hdr)).encode()),
                    'info': file_info
                }
        return rasters

    @staticmethod
    def validate_raster_dates(rasters):
        dates = set()
        for key, raster in rasters.items():
            dates.add(raster['info'].date)

        if len(dates) > 1:
            raise SNODASError(
                "SNODAS rasters not all from same date per filenames",
            )

        return dates.pop()
