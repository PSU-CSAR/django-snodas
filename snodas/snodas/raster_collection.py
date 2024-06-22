from collections.abc import Iterator
from datetime import date
from typing import Self

from django.conf import settings

from snodas import types
from snodas.snodas.db import get_raster_database
from snodas.snodas.fileinfo import Product, SNODASFileInfo
from snodas.snodas.raster import SNODASRaster


class RasterCollection:
    def __init__(
        self: Self,
        query: types.DateQuery,
        rasters: dict[Product, list[SNODASRaster]],
    ) -> None:
        self.query = query
        self._by_product = {
            product: sorted(rasters, key=lambda x: x.fileinfo.datetime)
            for product, rasters in rasters.items()
        }
        self._by_date: dict[date, list[SNODASRaster]] = {}
        for rasters_ in self._by_product.values():
            for raster in rasters_:
                try:
                    self._by_date[raster.fileinfo.datetime.date()].append(raster)
                except KeyError:
                    self._by_date[raster.fileinfo.datetime.date()] = [raster]

        self.validate()

    @property
    def products(self: Self) -> set[Product]:
        return set(self._by_product.keys())

    @property
    def dates(self: Self) -> list[date]:
        return sorted(self._by_date.keys())

    def __iter__(self: Self) -> Iterator[SNODASRaster]:
        for rasters in self._by_product.values():
            yield from rasters

    def __len__(self: Self) -> int:
        return sum(len(rasters) for rasters in self._by_product.values())

    @classmethod
    def from_products_query(
        cls: type[Self],
        query: types.DateQuery,
        products: set[Product],
    ) -> Self:
        rasterdb = get_raster_database(settings.SNODAS_RASTERDB)
        return cls(
            query=query,
            rasters={
                product: [
                    SNODASRaster(SNODASFileInfo(path))
                    for path in rasterdb.raster_paths_from_query(query, product)
                ]
                for product in products
            },
        )

    def validate(self: Self) -> None:
        if not len({len(rasters) for rasters in self._by_product.values()}) == 1:
            raise ValueError('Product raster lists are not all the same length')

        products = sorted(self.products)
        for date_, rasters in self._by_date.items():
            actual_products: list[Product] = sorted(
                raster.fileinfo.product for raster in rasters
            )
            if not products == actual_products:
                raise ValueError(
                    f"Unexpected product set for date '{date_}': "
                    f'{products} != {actual_products}',
                )
