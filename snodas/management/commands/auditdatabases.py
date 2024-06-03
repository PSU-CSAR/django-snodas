from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import date
from typing import Self

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from snodas import types
from snodas.snodas.db import get_raster_database
from snodas.snodas.fileinfo import Product, SNODASFileInfo


@dataclass
class RasterTracker:
    swe: bool = False
    depth: bool = False
    runoff: bool = False
    sublimation: bool = False
    sublimation_blowing: bool = False
    precip_solid: bool = False
    precip_liquid: bool = False
    average_temp: bool = False

    @classmethod
    def from_raster_db(
        cls: type[Self],
        rasters: Iterable[SNODASFileInfo],
    ) -> dict[date, Self]:
        _rs: dict[date, list[SNODASFileInfo]] = {}
        for raster in rasters:
            try:
                _rs[raster.datetime.date()].append(raster)
            except KeyError:
                _rs[raster.datetime.date()] = [raster]

        return {
            date_: cls(
                **{r.product.value: True for r in rasters},
            )
            for date_, rasters in _rs.items()
        }

    @classmethod
    def from_pg_rows(cls: type[Self], rows) -> dict[date, Self]:
        return {
            row[0]: cls(
                swe=row[1],
                depth=row[2],
                runoff=row[3],
                sublimation=row[4],
                sublimation_blowing=row[5],
                precip_solid=row[6],
                precip_liquid=row[7],
                average_temp=row[8],
            )
            for row in rows
        }

    def missing(self: Self) -> list[Product]:
        return [Product(product) for product, has in asdict(self).items() if not has]


class Command(BaseCommand):
    help = (
        'Create the raster database for SNODAS COGs, AOI rasters, '
        'and other required datasets.'
    )

    requires_system_checks = []  # type: ignore  # noqa: RUF012
    can_import_settings = True

    def handle(self: Self, *_, **__) -> None:
        self.raster_db = get_raster_database(settings.SNODAS_RASTERDB)
        aoi_diff = self.diff_aois()
        snodas_diff = self.diff_snodas()
        diff = aoi_diff or snodas_diff

        if diff:
            print('⚠️ DATABASES DIFFER ⚠️. See above for details.')  # noqa: T201
        else:
            print('✅ DATABASES MATCH  ✅. Congratulations.')  # noqa: T201

    def diff_aois(self: Self) -> bool:
        raster_db_aois = [aoi.station_triplet for aoi in self.raster_db.aoi_rasters()]
        pg_aois = self.get_pg_aois()

        raster_db_aoi_set: set[types.StationTriplet] = set()
        for triplet in raster_db_aois:
            if triplet in raster_db_aoi_set:
                print(f"raster db: duplicate AOI '{triplet}'")  # noqa: T201
            else:
                raster_db_aoi_set.add(triplet)

        pg_aoi_set: set[types.StationTriplet] = set()
        for triplet in pg_aois:
            if triplet in pg_aoi_set:
                print(f"postgres: duplicate AOI '{triplet}'")  # noqa: T201
            else:
                pg_aoi_set.add(triplet)

        aoi_diff: bool = False
        for triplet in pg_aoi_set - raster_db_aoi_set:
            aoi_diff = True
            print(f"raster db: missing AOI '{triplet}'")  # noqa: T201

        for triplet in raster_db_aoi_set - pg_aoi_set:
            aoi_diff = True
            print(f"postgres: missing AOI '{triplet}'")  # noqa: T201

        if not aoi_diff:
            print('raster db and postgres have same AOI sets')  # noqa: T201

        return aoi_diff

    def diff_snodas(self: Self) -> bool:
        rdb_rasters = RasterTracker.from_raster_db(
            self.raster_db.snodas_rasters(),
        )
        pg_rasters = RasterTracker.from_pg_rows(self.get_pg_rasters())

        for date_, raster in rdb_rasters.items():
            for missing in raster.missing():
                print(f"raster db: date {date_} missing '{missing}'")  # noqa: T201

        for date_, raster in pg_rasters.items():
            for missing in raster.missing():
                print(f"postgres: date {date_} missing '{missing}'")  # noqa: T201

        raster_diff: bool = False
        for date_ in set(pg_rasters) - set(rdb_rasters):
            raster_diff = True
            print(f"raster db: missing raster '{date_}'")  # noqa: T201

        for date_ in set(rdb_rasters) - set(pg_rasters):
            raster_diff = True
            print(f"postgres: missing raster '{date_}'")  # noqa: T201

        return raster_diff

    @staticmethod
    def get_pg_aois() -> list[types.StationTriplet]:
        with connection.cursor() as cursor:
            cursor.execute(
                'select awdb_id from pourpoint.pourpoint ' 'where polygon is not null',
            )
            return [types.StationTriplet(row[0]) for row in cursor.fetchall()]

    @staticmethod
    def get_pg_rasters():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    date,
                    swe is not null,
                    depth is not null,
                    runoff is not null,
                    sublimation is not null,
                    sublimation_blowing is not null,
                    precip_solid is not null,
                    precip_liquid is not null,
                    average_temp is not null
                from snodas.raster
                """,
            )
            return cursor.fetchall()
