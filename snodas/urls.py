from __future__ import annotations

from enum import StrEnum
from io import StringIO
from typing import Self

from django.conf import settings
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.urls import path, reverse
from ninja import NinjaAPI, Query
from ninja.errors import HttpError
from ninja.responses import Response

from snodas import types
from snodas.snodas.fileinfo import Product
from snodas.utils.http import stream_file
from snodas.views import (
    pourpoints,
    stats,
    tiles,
)


class ResponseFormat(StrEnum):
    JSON = 'json'
    CSV = 'csv'

    @classmethod
    def from_request(cls: type[Self], request: HttpRequest) -> ResponseFormat:
        # default to application/json, even if not explicitly accepted
        # only fall down to csv if it is accepted and json is not
        # have to check it first for Accepts values like */*
        if request.accepts('application/json') or not request.accepts('text/csv'):
            return cls.JSON
        return cls.CSV


api = NinjaAPI()


# API root
@api.get(
    '/',
    response=types.LandingPage,
    exclude_none=True,
)
def api_root(request: HttpRequest) -> types.LandingPage:
    return types.LandingPage(
        title=(
            'Portland State University (PSU) Center for Spatial '
            'Analysis and Research (CSAR) SNODAS tools API'
        ),
        description=('API providing pourpoint/AOI metadata and SNODAS statistics'),
        links=[
            types.Link(
                href=request.build_absolute_uri(
                    reverse(f'{api.urls_namespace}:api_root'),
                ),
                title='API Root',
                type='application/json',
                rel='self',
            ),
            types.Link(
                href=request.build_absolute_uri(
                    reverse(f'{api.urls_namespace}:openapi-json'),
                ),
                title='OpenAPI JSON Spec',
                type='application/json',
                rel='service-desc',
            ),
            types.Link(
                href=request.build_absolute_uri(
                    reverse(f'{api.urls_namespace}:openapi-view'),
                ),
                title='Interactive API Documentation',
                type='text/html',
                rel='service-doc',
            ),
            types.Link(
                href=request.build_absolute_uri(
                    reverse(f'{api.urls_namespace}:get_pourpoints'),
                ),
                title='List all pourpoints',
                type='application/geo+json',
            ),
        ],
    )


# Tile routes
@api.get(
    '/tiles/',
    response=tiles.DateList,
    include_in_schema=settings.DEBUG,
)
def tiles_list_dates(
    request: HttpRequest,
):
    return tiles.list_dates()


@api.get(
    '/tiles/{date}/{zoom}/{x}/{y}.png',
    include_in_schema=settings.DEBUG,
)
def get_tile(
    request: HttpRequest,
    date: types.Date,
    zoom: types.Zoom,
    x: int,
    y: int,
):
    return HttpResponse(
        tiles.get_tile(date, zoom, x, y),
        content_type='application/png',
    )


# Pourpoint routes
@api.get(
    '/pourpoints/',
    response=types.PourPoints,
    exclude_none=True,
)
def get_pourpoints(
    request: HttpRequest,
    response: HttpResponse,
):
    response['Content-Type'] = 'application/geo+json'
    return pourpoints.get_points().build_links(request, api)


@api.get(
    '/pourpoints/{zoom}/{x}/{y}.mvt',
    include_in_schema=settings.DEBUG,
)
def get_pourpoint_tile(
    request: HttpRequest,
    zoom: types.Zoom,
    x: int,
    y: int,
):
    return HttpResponse(
        pourpoints.get_tile(zoom, x, y),
        content_type='application/vnd.mapbox-vector-tile',
    )


@api.get(
    '/pourpoints/{pourpoint_id}/',
    response=types.PourPoint,
    exclude_none=True,
)
def get_pourpoint_by_id(
    request: HttpRequest,
    pourpoint_id: int,
    response: HttpResponse,
):
    response['Content-Type'] = 'application/geo+json'
    return pourpoints.get_point(pourpoint_id).build_links(request, api, full=True)


@api.get(
    '/pourpoints/by-triplet/{station_triplet}/',
    response=types.PourPoint,
    exclude_none=True,
)
def get_pourpoint_by_triplet(
    request: HttpRequest,
    station_triplet: types.StationTriplet,
    response: HttpResponse,
):
    response['Content-Type'] = 'application/geo+json'
    return pourpoints.get_point(station_triplet).build_links(
        request,
        api,
        full=True,
        from_triplet=True,
    )


def basic_stats(
    request: HttpRequest,
    pourpoint_id: int,
    query: types.PourPointQuery,
    response_format: ResponseFormat = ResponseFormat.JSON,
) -> HttpResponse | StreamingHttpResponse:
    pourpoint = pourpoints.get_point(pourpoint_id).build_links(
        request,
        api,
    )

    if not pourpoint.properties.area_meters:
        raise HttpError(
            status_code=409,
            message='Pourpoint does not have an AOI polygon',
        )

    if response_format == ResponseFormat.JSON:
        return Response(
            types.PourPointStats(
                pourpoint=pourpoint,
                query=query,
                results=stats.get_pourpoint_stats(
                    pourpoint.id,
                    query,
                ),
            )
            .build_links(
                request,
                api,
            )
            .model_dump(
                exclude_unset=True,
                exclude_none=True,
            ),
        )

    return stats.get_csv_statistics(
        request,
        pourpoint_id,
        query,
    )


@api.get(
    '/pourpoints/{pourpoint_id}/stats/date-range',
    response=types.PourPointStats,
    exclude_none=True,
)
def id_stat_range_query(
    request: HttpRequest,
    pourpoint_id: int,
    start_date: types.Date,
    end_date: types.Date,
    format: ResponseFormat | None = None,
) -> HttpResponse | StreamingHttpResponse:
    query = types.DateRangeQuery(
        start_date=start_date,
        end_date=end_date,
    )

    return basic_stats(
        request=request,
        pourpoint_id=pourpoint_id,
        query=query,
        response_format=(format if format else ResponseFormat.from_request(request)),
    )


@api.get(
    '/pourpoints/{pourpoint_id}/stats/doy',
    response=types.PourPointStats,
    exclude_none=True,
)
def id_stat_doy_query(
    request: HttpRequest,
    pourpoint_id: int,
    month: types.Month,
    day: types.Day,
    start_year: types.Year = 2004,
    end_year: types.Year = 9999,
    format: ResponseFormat | None = None,
) -> HttpResponse | StreamingHttpResponse:
    query = types.DOYQuery(
        month=month,
        day=day,
        start_year=start_year,
        end_year=end_year,
    )

    return basic_stats(
        request=request,
        pourpoint_id=pourpoint_id,
        query=query,
        response_format=(format if format else ResponseFormat.from_request(request)),
    )


def zonal_stats(
    request: HttpRequest,
    pourpoint_id: int,
    query: types.PourPointQuery,
    products: Query[list[Product]],
    elevation_band_step_ft: int = 1000,
    response_format: ResponseFormat = ResponseFormat.JSON,
) -> HttpResponse | StreamingHttpResponse:
    # deduplicate products
    products = list(set(products))

    pourpoint = pourpoints.get_point(pourpoint_id).build_links(
        request,
        api,
    )

    if not pourpoint.properties.area_meters:
        raise HttpError(
            status_code=409,
            message='Pourpoint does not have an AOI polygon',
        )

    results = stats.get_pourpoint_zonal_stats(
        pourpoint.properties.station_triplet,
        query,
        products,
        elevation_band_step_feet=elevation_band_step_ft,
    )

    if response_format == ResponseFormat.JSON:
        return Response(
            types.PourPointZonalStats(
                pourpoint=pourpoint,
                products=products,
                query=query,
                results=results.dump(),
            )
            .build_links(
                request,
                api,
            )
            .model_dump(
                exclude_unset=True,
                exclude_none=True,
            ),
        )

    flike = StringIO()
    results.dump_to_csv(flike)
    return stream_file(
        flike,
        query.csv_name(pourpoint.properties.name, zone_size=elevation_band_step_ft),
        request,
        'text/csv',
    )


@api.get(
    '/pourpoints/{pourpoint_id}/zonal-stats/date-range',
    response=types.PourPointZonalStats,
    exclude_none=True,
    exclude_unset=True,
)
def zonal_stat_range_query(
    request: HttpRequest,
    pourpoint_id: int,
    products: Query[list[Product]],
    start_date: types.Date,
    end_date: types.Date,
    elevation_band_step_ft: int = 1000,
    format: ResponseFormat | None = None,
) -> HttpResponse | StreamingHttpResponse:
    query = types.DateRangeQuery(
        start_date=start_date,
        end_date=end_date,
    )

    return zonal_stats(
        request,
        pourpoint_id,
        query,
        products,
        elevation_band_step_ft,
        response_format=(format if format else ResponseFormat.from_request(request)),
    )


@api.get(
    '/pourpoints/{pourpoint_id}/zonal-stats/doy',
    response=types.PourPointZonalStats,
    exclude_none=True,
    exclude_unset=True,
)
def zonal_stat_doy_query(
    request: HttpRequest,
    pourpoint_id: int,
    products: Query[list[Product]],
    month: types.Month,
    day: types.Day,
    start_year: types.Year = 2004,
    end_year: types.Year = 9999,
    elevation_band_step_ft: int = 1000,
    format: ResponseFormat | None = None,
) -> HttpResponse | StreamingHttpResponse:
    query = types.DOYQuery(
        month=month,
        day=day,
        start_year=start_year,
        end_year=end_year,
    )

    return zonal_stats(
        request,
        pourpoint_id,
        query,
        products,
        elevation_band_step_ft,
        response_format=(format if format else ResponseFormat.from_request(request)),
    )


# legacy query endpoints for UI
@api.get(
    '/query/pourpoint/polygon/{pourpoint_id}/{start_date}/{end_date}/',
    include_in_schema=settings.DEBUG,
)
def legacy_range_query(
    request: HttpRequest,
    pourpoint_id: int,
    start_date: types.Date,
    end_date: types.Date,
):
    return stats.get_csv_statistics(
        request,
        pourpoint_id,
        types.DateRangeQuery(
            start_date=start_date,
            end_date=end_date,
        ),
    )


@api.get(
    '/query/pourpoint/polygon/{pourpoint_id}/{monthday}/{start_year}/{end_year}/',
    include_in_schema=settings.DEBUG,
)
def legacy_doy_query(
    request: HttpRequest,
    pourpoint_id: int,
    monthday: str,
    start_year: types.Year,
    end_year: types.Year,
):
    month = int(monthday[:2])
    day = int(monthday[-2:])
    return stats.get_csv_statistics(
        request,
        pourpoint_id,
        types.DOYQuery(
            month=month,
            day=day,
            start_year=start_year,
            end_year=end_year,
        ),
    )


@api.get(
    '/analysis/streamflow/{snodas_variable}/{forecast_start_month}/{forecast_end_month}/{monthday}/{start_year}/{end_year}/',
    include_in_schema=settings.DEBUG,
)
def streamflow(
    request: HttpRequest,
    snodas_variable: types.SnodasVariable,
    forecast_start_month: types.Month,
    forecast_end_month: types.Month,
    monthday: str,
    start_year: types.Year,
    end_year: types.Year,
):
    month = int(monthday[:2])
    day = int(monthday[-2:])
    return stats.streamflow_regression(
        request,
        snodas_variable,
        forecast_start_month,
        forecast_end_month,
        month,
        day,
        start_year,
        end_year,
    )


urlpatterns = [
    path('', api.urls),
]
