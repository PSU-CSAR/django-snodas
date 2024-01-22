import re

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Self

from snodas.snodas.raster import SNODASRaster


class Region(StrEnum):
    US = 'us'
    MASKED = 'zz'


class Model(StrEnum):
    SSM = 'ssm'


class Datatype(StrEnum):
    V0 = 'v0'  # driving input
    V1 = 'v1'  # model output


class Timecode(StrEnum):
    T0024 = '0024'  # 24 hr integration
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

_product_name_to_product_code = {v: k for k, v in _product_code_to_product_name.items()}


@dataclass
class Unit:
    name: str
    scale_factor: int

    def scale(self: Self, value: float | int) -> float:
        return value / self.scale_factor


_millimeters = Unit(name='mm', scale_factor=1)
_millimeters_100 = Unit(name='mm', scale_factor=100)
_kelvin = Unit(name='mm', scale_factor=1)
_kg_per_meter2 = Unit(name='kg_per_m2', scale_factor=10)

_units = {
    'precip_solid': _kg_per_meter2,
    'precip_liquid': _kg_per_meter2,
    'swe': _millimeters,
    'depth': _millimeters,
    'average_temp': _kelvin,
    'sublimation': _millimeters_100,
    'sublimation_blowing': _millimeters_100,
    'runoff': _millimeters_100,
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

    def to_glob(self: Self) -> str:
        product_name = self.value
        vcode: str = ''

        if product_name.startswith('precip'):
            product_name, precip_type = product_name.split('_')
            match precip_type:
                case 'liquid':
                    vcode = 'lL00'
                case 'solid':
                    vcode = 'lL01'
                case _:
                    raise ValueError(f"unknown precip type '{precip_type}'")

        product_code = _product_name_to_product_code[product_name]
        return ''.join(
            [
                '?' * 6,
                'v[01]',
                str(product_code),
                '?',
                vcode,
                '*TTNATS*.tif',
            ],
        )

    def unit(self: Self) -> Unit:
        return _units[self.value]


class BaseFileInfo:
    regex: ClassVar[re.Pattern[str]] = re.compile(
        r'^'
        r'(?P<region>[a-z]{2})_'
        r'(?P<model>[a-z]{3})'
        r'(?P<datatype>v\d)'
        r'(?P<product_code>\d{4})'
        r'(?P<scaled>S?)'
        r'(?P<vcode>[a-zA-Z]{2}[\d_]{2})'
        r'[AT](?P<timecode>00(01|24))'
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
        self.path = path
        self.name = self.path.stem
        info = self._match(self.name).groupdict()

        try:
            self.region = Region(info['region'])
            self.model = Model(info['model'])
            self.datatype = Datatype(info['datatype'])
            self.scaled = bool(info['scaled'])
            self.vcode: str = info['vcode']
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
        except Exception as e:
            raise ValueError('invalid value in SNODAS file name') from e

    @classmethod
    def _match(cls: type[Self], string: str):
        match = cls.regex.match(string)
        if not match:
            raise ValueError('unable to parse SNODAS file path')
        return match


class SNODASFileInfo(BaseFileInfo):
    def open(self: Self) -> SNODASRaster:
        return SNODASRaster(self)
