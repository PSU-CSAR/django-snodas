from datetime import datetime, date
from enum import auto, StrEnum
from typing import Annotated, Literal, Protocol, Self

from django.http import HttpRequest
from django.urls import reverse
from ninja import NinjaAPI

from psycopg2 import sql
from pydantic import AnyUrl, BaseModel, Field, PlainValidator, WithJsonSchema, field_serializer

YYYY = r'\d{4}'
MM = r'(0[1-9]|1[0-2])'
DD = r'(0[1-9]|[1-2][0-9]|3[0-1])'
DATE = f'{YYYY}-?{MM}-?{DD}'
STATION_TRIPLET = r'[a-zA-Z0-9\-]+:[a-zA-Z]{2}:[a-zA-Z]+'


class SnodasVariable(StrEnum):
    SWE = auto()
    DEPTH = auto()
    RUNOFF = auto()
    SUBLIMATION = auto()
    SUBLIMATION_BLOWING = auto()
    PRECIP_SOLID = auto()
    PRECIP_LIQUID = auto()
    AVERAGE_TEMP = auto()


def to_date(value: str) -> date:
    return datetime.strptime(
        value.replace('-', ''),
        '%Y%m%d',
    ).date()

Date = Annotated[
    date,
    PlainValidator(to_date),
    WithJsonSchema(
        {
            'type': 'string',
            'pattern': f'^{DATE}$',
            'example': '20230414',
            'description': 'Date in YYYYMMDD format',
        },
        mode='validation',
    ),
]

StationTriplet = Annotated[
    str,
    Field(
        pattern=f'^{STATION_TRIPLET}$',
    ),
    WithJsonSchema(
        {
            #'pattern': f'^{STATION_TRIPLET}$',
            'example': '12354500:MT:USGS',
        },
        mode='validation',
    ),
]

Month = Annotated[
    int,
    Field(..., ge=1, le=12),
]

Day = Annotated[
    int,
    Field(..., ge=1, le=31),
]

Year = Annotated[
    int,
    Field(..., ge=1, le=9999),
]

Zoom = Annotated[
    int,
    Field(..., ge=0, le=15),
]


class Link(BaseModel):
    href: AnyUrl
    title: str | None = None
    rel: str | None = None
    type: str | None = None

    def __init__(self, href: AnyUrl | str, **kwargs) -> None:
        super().__init__(href=href, **kwargs)

    @field_serializer('href')
    def serialize_href(self, href: AnyUrl) -> str:
        return str(href)


class PourPointProperties(BaseModel):
    name: str = Field(..., examples=['Clark Fork R at St. Regis'])
    station_triplet: StationTriplet
    area_meters: float | None = Field(..., examples=[27740389176.977703])


class Point(BaseModel):
    type: Literal['Point'] = 'Point'
    coordinates: tuple[float, float] = Field(
        ...,
        examples=[(-115.087346, 47.301864)],
    )


class PourPoint(BaseModel):
    type: Literal['Feature'] = 'Feature'
    id: int = Field(..., gt=0, examples=[1])
    geometry: Point
    properties: PourPointProperties
    links: list[Link] = []

    def build_links(
        self: Self,
        request: HttpRequest,
        api: NinjaAPI,
        full: bool = False,
        from_triplet: bool = False,
    ) -> Self:
        self.links = [
            Link(
                rel=('canonical' if from_triplet else 'self'),
                type='application/geo+json',
                href=request.build_absolute_uri(
                    reverse(
                        f'{api.urls_namespace}:get_pourpoint_by_id',
                        args=(self.id,),
                    ),
                ),
            ),
        ]

        if from_triplet:
            self.links.append(
                Link(
                    rel='self',
                    type='application/geo+json',
                    href=request.build_absolute_uri(
                        reverse(
                            f'{api.urls_namespace}:get_pourpoint_by_triplet',
                            args=(self.properties.station_triplet,),
                        ),
                    ),
                ),
            )

        if full and self.properties.area_meters:
            self.links.extend([
                Link(
                    rel='related',
                    type='application/json',
                    href=request.build_absolute_uri(
                        reverse(
                            f'{api.urls_namespace}:id_stat_range_query',
                            args=(self.id,),
                        ),
                    ),
                    title='Query AOI statistics by date range',
                ),
                Link(
                    rel='related',
                    type='application/json',
                    href=request.build_absolute_uri(
                        reverse(
                            f'{api.urls_namespace}:id_stat_doy_query',
                            args=(self.id,),
                        ),
                    ),
                    title='Query AOI statistics by day of year',
                ),
            ])

        if full:
            self.links.extend([
                Link(
                    rel='root',
                    type='application/json',
                    href=request.build_absolute_uri(
                        reverse(
                            f'{api.urls_namespace}:api_root',
                        ),
                    ),
                ),
            ])

        return self


class PourPoints(BaseModel):
    type: Literal['FeatureCollection'] = 'FeatureCollection'
    features: list[PourPoint]
    links: list[Link] = []

    def build_links(self: Self, request: HttpRequest, api: NinjaAPI) -> Self:
        self.links = [
            Link(
                rel='self',
                type='application/geo+json',
                href=request.build_absolute_uri(),
            ),
            Link(
                rel='root',
                type='application/json',
                href=request.build_absolute_uri(
                    reverse(
                        f'{api.urls_namespace}:api_root',
                    ),
                ),
            ),
        ]

        for feature in self.features:
            feature.build_links(request, api)

        return self


class SnodasStats(BaseModel):
    date: date
    swe: float
    depth: float
    runoff: float
    precip_solid: float
    precip_liquid: float
    sublimation: float
    sublimation_blowing: float
    average_temp: float


class DateQuery(Protocol):  # pragma: no cover
    def stat_query(self, pourpoint_id: int) -> sql.Composed: ...
    def csv_name(self, pourpoint_name: str) -> str: ...


class DateRangeQuery(BaseModel):
    type: Literal['DateRange'] = 'DateRange'
    start_date: date
    end_date: date

    def stat_query(self, pourpoint_id: int) -> sql.Composed:
        base_query: str = '''
            SELECT
                date,
                swe,
                depth,
                runoff,
                sublimation,
                sublimation_blowing,
                precip_solid,
                precip_liquid,
                average_temp
            FROM
                pourpoint.statistics
            WHERE
                pourpoint_id = {}
                AND {}::daterange @> date
            ORDER BY
                date
        '''

        daterange = f'[{self.start_date}, {self.end_date}]'
        query = sql.SQL(base_query).format(
            sql.Literal(pourpoint_id),
            sql.Literal(daterange),
        )
        return query

    def csv_name(self, pourpoint_name: str) -> str:
        return '{}_{}-{}.csv'.format(
            "-".join(pourpoint_name.split()),
            self.start_date,
            self.end_date,
        )

    def __str__(self) -> str:
        return f'{self.start_date}/{self.end_date}'


class DOYQuery(BaseModel):
    type: Literal['DayOfYear'] = 'DayOfYear'
    month: Month
    day: Day
    start_year: Year
    end_year: Year

    def stat_query(self, pourpoint_id: int) -> sql.Composed:
        base_query: str = '''
            SELECT
                date,
                swe,
                depth,
                runoff,
                sublimation,
                sublimation_blowing,
                precip_solid,
                precip_liquid,
                average_temp
            FROM
                pourpoint.statistics
            WHERE
                pourpoint_id = {}
                AND {}::int4range @> date_part('year', date)::integer
                AND {} = date_part('month', date)
                AND {} = date_part('day', date)
            ORDER BY
                date
        '''

        year_range = f'[{self.start_year}, {self.end_year}]'
        query = sql.SQL(base_query).format(
            sql.Literal(pourpoint_id),
            sql.Literal(year_range),
            sql.Literal(self.month),
            sql.Literal(self.day),
        )
        return query

    def csv_name(self, pourpoint_name: str) -> str:
        return '{}_{}-{}_{}-{}.csv'.format(
                "-".join(pourpoint_name.split()),
                self.month,
                self.day,
                self.start_year,
                self.end_year,
            )

    def __str__(self) -> str:
        return f'{self.month}{self.day}/{self.start_year}/{self.end_year}'


PourPointQuery = Annotated[
    DateRangeQuery | DOYQuery,
    Field(..., discriminator='type'),
]


class PourPointStats(BaseModel):
    pourpoint: PourPoint
    query: PourPointQuery
    results: list[SnodasStats] = Field(
        ...,
        examples=[[{
            'date': '2008-12-14',
            'swe': 0.018373034138853925,
            'depth': 0.12781884243276667,
            'runoff': 0.0000057251843327792756,
            'sublimation': -0.00012737501598261594,
            'average_temp': 266.3164421865995,
            'precip_solid': 6.18786387077508,
            'precip_liquid': 0.03673017090738538,
            'sublimation_blowing': -6.307803776158206e-8,
        }]],
    )
    links: list[Link] = []

    def build_links(self: Self, request: HttpRequest, api: NinjaAPI) -> Self:
        self.links = [
            Link(
                rel='self',
                type='application/json',
                href=request.build_absolute_uri(),
            ),
            Link(
                rel='root',
                type='application/json',
                href=request.build_absolute_uri(
                    reverse(
                        f'{api.urls_namespace}:api_root',
                    ),
                ),
            ),
        ]
        self.pourpoint.build_links(request, api)
        return self


class LandingPage(BaseModel):
    title: str
    description: str
    links: list[Link]
