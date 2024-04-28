import gzip
import shutil
import tarfile

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.gis.db.backends.postgis.pgraster import to_pgraster
from django.contrib.gis.gdal import GDALRaster
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from snodas.exceptions import SNODASError
from snodas.management import utils
from snodas.snodas.fileinfo import Product, SNODASFileInfo
from snodas.utils.filesystem import tempdirectory

HDR_EXTS = ('.Hdr', '.txt')


@dataclass
class Raster:
    raster: BytesIO
    info: SNODASFileInfo


class Command(BaseCommand):
    help = """Load a SNODAS rasters into the database.
    Simply provide the path to a SNODAS daily tarfile
    and this command will do the rest."""

    requires_system_checks = []  # type: ignore  # noqa: RUF012
    can_import_settings = True

    table = 'snodas.raster'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            'snodas_tar',
            type=utils.file,
            help='Path to a SNODAS tarfile.',
        )
        parser.add_argument(
            '-o',
            '--output-dir',
            type=utils.directory,
            help=(
                'Path to a directory in which to retain the expanded files. '
                'Default is to use a temp directory deleted on exit.'
            ),
        )

    def handle(self, *_, **options) -> None:
        if settings.DEBUG:
            raise CommandError(
                'Debug logging can cause problems for loadraster. '
                'Turn off DEBUG before running loadraster.',
            )
        rasters = self.extract_snodas_data(
            options['snodas_tar'],
            outdir=options.get('output_dir', None),
        )
        date = self.validate_raster_dates(rasters)

        try:
            # order is important, as it must match the table column order
            raster_streams: list[BytesIO] = [
                rasters[Product.SNOW_WATER_EQUIVALENT].raster,
                rasters[Product.SNOW_DEPTH].raster,
                rasters[Product.RUNOFF].raster,
                rasters[Product.SUBLIMATION].raster,
                rasters[Product.SUBLIMATION_BLOWING].raster,
                rasters[Product.PRECIP_SOLID].raster,
                rasters[Product.PRECIP_LIQUID].raster,
                # early data have missing average temp
                # (and also has a funky undocumented grid)
                # but all modern data should have it
                rasters[Product.AVERAGE_TEMP].raster,
            ]
        except KeyError as e:
            raise SNODASError('SNODAS data appears incomplete') from e

        raster_streams.append(BytesIO(date.encode()))
        ftype = utils.chain_streams(raster_streams, sep=b'\t')

        print(f'Inserting record into database for date {date}')  # noqa: T201
        with connection.cursor() as cursor:
            try:
                cursor.copy_expert(f'copy {self.table} from stdin', ftype)
                del rasters
            except KeyError as e:
                raise SNODASError('SNODAS data appears incomplete') from e

        print('Processing completed successfully')  # noqa: T201

    @staticmethod
    def trim_header(hdr: Path):
        """gdal has a header line length limit of
        256 chars for <2.3.0, or 1024 chars for >=2.3.0,
        but we trim to the smaller size to be safe."""
        line_limit = 255
        lines: list[bytes] = []
        with hdr.open('b') as f:
            for line in f:
                lines.append(line[: min(len(line), line_limit)] + '\n')

        with hdr.open('wb') as f:
            f.writelines(lines)

    def extract_snodas_data(self, snodas_tar: Path, outdir: Path | None = None):
        rasters: dict[Product, Raster] = {}

        with tempdirectory() as _temp:
            temp = Path(_temp)

            if not outdir:
                outdir = temp

            tar = tarfile.open(snodas_tar)
            print(f'Extracting {snodas_tar}\n\tto temp dir {temp}')  # noqa: T201
            tar.extractall(temp, filter='data')

            gzipped = list(temp.glob('*.gz'))
            for idx, f in enumerate(gzipped, start=1):
                print(f'Unzipping file {idx} of {len(gzipped)}: {f.name}')  # noqa: T201
                outpath = outdir / f.stem
                with gzip.open(f, 'rb') as f_in, outpath.open('wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            hdrs: list[Path] = []
            for ext in HDR_EXTS:
                hdrs.extend(outdir.glob(f'*{ext}'))

            for idx, hdr in enumerate(hdrs, start=1):
                print(f'Importing {idx} of {len(hdrs)}: {hdr.name}')  # noqa: T201
                self.trim_header(hdr)
                file_info = SNODASFileInfo(hdr)
                rasters[file_info.product] = Raster(
                    raster=BytesIO(to_pgraster(GDALRaster(hdr)).hex().encode()),
                    info=file_info,
                )
        return rasters

    @staticmethod
    def validate_raster_dates(rasters):
        dates = set()
        for raster in rasters.values():
            dates.add(raster['info'].date)

        if len(dates) > 1:
            raise SNODASError(
                'SNODAS rasters not all from same date per filenames',
            )

        return dates.pop()
