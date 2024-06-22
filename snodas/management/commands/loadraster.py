from pathlib import Path
from typing import Self

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from snodas.management import utils
from snodas.snodas.db import get_raster_database
from snodas.snodas.input_rasters import SNODASInputRasterSet
from snodas.utils.filesystem import tempdirectory

HDR_EXTS = ('.Hdr', '.txt')


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
            '--skip-legacy-db',
            action='store_true',
            default=False,
            help='Do not write raster to legacy database',
        )
        parser.add_argument(
            '--skip-raster-db',
            action='store_true',
            default=False,
            help='Do not write raster to filesystem raster database',
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
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help='Allow overwriting existing files (rasterdb only)',
        )

    def handle(self, *_, **options) -> None:
        write_pg = not options['skip_legacy_db']
        write_rasterdb = not options['skip_raster_db']
        force = options['force']

        # if DEBUG is enabled and we write to the database
        # the writing of the raster data to the log will
        # cause the db insert to fail/thing to go wrong
        if write_pg and settings.DEBUG:
            raise CommandError(
                'Debug logging can cause problems for loadraster. '
                'Turn off DEBUG before running loadraster.',
            )

        with tempdirectory() as tempdir:
            raster_set = SNODASInputRasterSet.from_archive(
                snodas_tar=options['snodas_tar'],
                extract_dir=(options.get('output_dir') or Path(tempdir)),
            )

            if write_rasterdb:
                self._write_rasterdb(raster_set, force=force)

            if write_pg:
                self._write_pg(raster_set)

        print('Processing completed successfully.')  # noqa: T201

    def _write_rasterdb(
        self: Self,
        raster_set: SNODASInputRasterSet,
        force: bool,
    ) -> None:
        print('Importing rasters into raster db...')  # noqa: T201
        raster_db = get_raster_database(settings.SNODAS_RASTERDB)
        raster_db.import_snodas_rasters(raster_set, force=force)

    def _write_pg(self: Self, raster_set: SNODASInputRasterSet) -> None:
        print('Inserting record into legacy database...')  # noqa: T201
        with connection.cursor() as cursor:
            cursor.copy_expert(
                f'copy {self.table} from stdin',
                raster_set.get_bytes_stream(),
            )
