from argparse import ArgumentParser
from pathlib import Path
from typing import Self

from django.conf import settings
from django.core.management.base import BaseCommand

from snodas.management import utils
from snodas.snodas.db import RasterDatabase


class Command(BaseCommand):
    help = (
        'Create the raster database for SNODAS COGs, AOI rasters, '
        'and other required datasets.'
    )

    requires_system_checks = []  # type: ignore  # noqa: RUF012
    can_import_settings = True

    def add_arguments(self: Self, parser: ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            '--dem',
            required=True,
            type=utils.path_exists,
            help='Path to reference DEM layer',
        )
        parser.add_argument(
            '-F',
            '--force',
            action='store_true',
            default=False,
            help='Attempt database creation even if already exists',
        )

    def handle(self: Self, dem: Path, *_, force: bool = False, **__) -> None:
        RasterDatabase.create(
            path=settings.SNODAS_RASTERDB,
            input_dem_path=dem,
            force=force,
        )
