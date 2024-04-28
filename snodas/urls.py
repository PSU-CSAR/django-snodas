from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import path, reverse
from ninja import NinjaAPI
from ninja.errors import HttpError

from snodas import types
from snodas.views import (
    pourpoints,
    stats,
    tiles,
)

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
        request, api, full=True, from_triplet=True,
    )


@api.get(
    '/pourpoints/{pourpoint_id}/stats/date-range',  # /{start_date}/{end_date}/',
    response=types.PourPointStats,
    exclude_none=True,
)
def id_stat_range_query(
    request: HttpRequest,
    pourpoint_id: int,
    start_date: types.Date,
    end_date: types.Date,
) -> types.PourPointStats:
    pourpoint = pourpoints.get_point(pourpoint_id).build_links(
        request,
        api,
    )

    if not pourpoint.properties.area_meters:
        raise HttpError(
            status_code=409,
            message='Pourpoint does not have an AOI polygon',
        )

    query = types.DateRangeQuery(
        start_date=start_date,
        end_date=end_date,
    )
    return types.PourPointStats(
        pourpoint=pourpoint,
        query=query,
        results=stats.get_pourpoint_stats(
            pourpoint.id,
            query,
        ),
    ).build_links(request, api)


@api.get(
    '/pourpoints/{pourpoint_id}/stats/doy',  # /{month}/{day}/{start_year}/{end_year}/',
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
):
    pourpoint = pourpoints.get_point(pourpoint_id).build_links(
        request,
        api,
    )

    if not pourpoint.properties.area_meters:
        raise HttpError(
            status_code=409,
            message='Pourpoint does not have an AOI polygon',
        )

    query = types.DOYQuery(
        month=month,
        day=day,
        start_year=start_year,
        end_year=end_year,
    )
    return types.PourPointStats(
        pourpoint=pourpoint,
        query=query,
        results=stats.get_pourpoint_stats(
            pourpoint.id,
            query,
        ),
    ).build_links(request, api)


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
