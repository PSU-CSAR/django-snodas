from typing import Self

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from snodas.snodas.aoi import AOI
from snodas.snodas.db import get_raster_database


class Command(BaseCommand):
    help = (
        'Load a BAGIS geojson-format pourpoint into the database. '
        'Simply provide the path to a pourpoint geojson file. '
        'Also allows updating an existing pourpoint with the update option.'
    )

    requires_system_checks = []  # type: ignore  # noqa: RUF012
    can_import_settings = True

    table = 'pourpoint.pourpoint'

    def add_arguments(self: Self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            'aoi',
            metavar='pourpoint_geojson',
            type=AOI.from_geojson,
            help='Path to a BAGIS pourpoint geojson file.',
        )
        parser.add_argument(
            '-u',
            '--update',
            action='store_true',
            default=False,
            help=(
                'Allow updates to a existing pourpoint. '
                'Default behavior will error on conflict.'
            ),
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
            '-d',
            '--dry-run',
            action='store_true',
            default=False,
            help="Don't execute insert, just dump sql command",
        )

    def handle(
        self: Self,
        *_,
        aoi: AOI,
        skip_raster_db: bool = False,
        skip_legacy_db: bool = False,
        dry_run: bool = False,
        update: bool = False,
        **__,
    ) -> None:
        if not dry_run and not skip_raster_db and aoi.polygon is not None:
            self._write_rasterdb(aoi, update=update)

        if not skip_legacy_db:
            self._write_pg(aoi, update=update, dry_run=dry_run)

    def _write_rasterdb(self: Self, aoi: AOI, update: bool):
        raster_db = get_raster_database(settings.SNODAS_RASTERDB)
        raster_db.rasterize_aoi(aoi, force=update)

    def _write_pg(self: Self, aoi: AOI, update: bool, dry_run: bool) -> None:
        print(f"Inserting pourpoint into database '{aoi.station_triplet}'")  # noqa: T201

        sql, params = aoi.insert_sql(
            table=self.table,
            allow_update=update,
        )

        if dry_run:
            print(f'SQL: {sql}')  # noqa: T201
            print(f'PARAMS: {params}')  # noqa: T201
            return

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
