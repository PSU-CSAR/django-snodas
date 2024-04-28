import re

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Self


class Region(StrEnum):
    US = 'us'
    MASKED = 'zz'


class Model(StrEnum):
    SSM = 'ssm'


class Datatype(StrEnum):
    V0 = 'v0'  # driving input
    V1 = 'v1'  # model output


class Timecode(StrEnum):
    T0024 =  '0024'  # 24 hr integration
    T0001 = '0001'  # 1 hr snapshot


class Interval(StrEnum):
    HOUR = 'H'
    DAY = 'D'


class Offset(StrEnum):
    P001 = 'P001'  # value is delta over interval or value at interval end
    P000 = 'P000'  # value from interval start


_product_code_to_product_name = {
    1025: 'precip',
    1034: 'swe',
    1036: 'depth',
    1038: 'average_temp',
    1039: 'sublimation_blowing',
    1044: 'runoff',
    1050: 'sublimation',
}


class Product(StrEnum):
    PRECIP_SOLID = 'precip_solid'
    PRECIP_LIQUID = 'precip_liquid'
    SNOW_WATER_EQUIVALENT = 'swe'
    SNOW_DEPTH = 'depth'
    AVERAGE_TEMP = 'average_temp'
    SUBLIMATION = 'sublimation'
    SUBLIMATION_BLOWING = 'sublimation_blowing'
    RUNOFF = 'runoff'

    @classmethod
    def from_product_codes(cls: type[Self], product_code: int, vcode: str) -> Self:
        product_name: str = _product_code_to_product_name[product_code]

        if product_name != 'precip':
            return cls(product_name)

        match vcode:
            case 'lL00':
                return cls('precip_liquid')
            case 'lL01':
                return cls('precip_solid')
            case _:
                raise ValueError(
                    f"unknown vcode '{vcode}' for product type 'precip'",
                )


class SNODASFileInfo:
    regex = re.compile(
        r'^'
        r'(?P<region>[a-z]{2})_'
        r'(?P<model>[a-z]{3})'
        r'(?P<datatype>v\d)'
        r'(?P<product_code>\d{4})'
        r'(?P<scaled>S?)'
        r'(?P<vcode>[a-zA-Z]{2}[\d_]{2})'
        r'(?P<timecode>[AT]00[02][14])'
        r'TTNATS'
        r'(?P<year>\d{4})'
        r'(?P<month>\d{2})'
        r'(?P<day>\d{2})'
        r'(?P<hour>\d{2})'
        r'(?P<interval>H|D)'
        r'(?P<offset>P00[01])'
        r'$',
    )

    def __init__(self: Self, path: Path) -> None:
        self.name: str = path.stem
        match = self._match(self.name)

        if not match:
            raise ValueError('unable to parse SNODAS file path')

        info = match.groupdict()

        try:
            self.region = Region(info['region'])
            self.model = Model(info['model'])
            self.datatype = Datatype(info['datatype'])
            self.scaled = info['scaled']
            self.vcode = info['vcode']
            self.timecode = Timecode(info['timecode'])
            self.datetime = datetime(
                year=int(info['year']),
                month=int(info['month']),
                day=int(info['day']),
                hour=int(info['hour']),
                tzinfo=UTC,
            )
            self.interval = Interval(info['interval'])
            self.offset = Offset(info['offset'])
            self.product = Product.from_product_codes(
                int(info['product_code']),
                self.vcode,
            )
        except Exception as e:  # noqa: BLE001
            raise ValueError('invalid value in SNODAS file name') from e

    @classmethod
    def _match(cls, string: str):
        return cls.regex.match(string)
