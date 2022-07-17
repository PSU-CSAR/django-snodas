from django.urls import include, re_path

from .settings import REST_ROOT, DEBUG, INSTALLED_APPS

from .views import snodas_tiles, pourpoints, snodas_stats, snodas_analysis

from .constants import snodas_variables


# TODO: change these to be django url convertors
# see https://docs.djangoproject.com/en/2.1/topics/http/urls/#registering-custom-path-converters
# url regex patterns
LAT = r'(\+|-)?(?:90(?:(?:\.0*)?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]*)?))'
LONG = r'(\+|-)?(?:180(?:(?:\.0*)?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]*)?))'
YYYY = r'\d{4}'
MM = r'(0[1-9]|1[0-2])'
DD = r'(0[1-9]|[1-2][0-9]|3[0-1])'
YYYYMMDD = r'{YYYY}-?{MM}-?{DD}'.format(YYYY=YYYY, MM=MM, DD=DD)
ZOOM = r'[0]?[0-9]|1[0-5]'
X = r'\d+'
Y = r'\d+'
ID = r'\d+'
SNODAS_VARS = "|".join(snodas_variables)

rest_urls = [
    # find all snodas dates
    re_path(
        r'^tiles/$',
        snodas_tiles.list_dates,
    ),

    # snodas start, end, and missing dates (legacy)
    re_path(
        r'^tiles/date-params$',
        snodas_tiles.date_params,
    ),

    # snodas raster tiles by date
    re_path(
        r'^tiles/(?P<date>{DATE})/(?P<zoom>{ZOOM})/(?P<x>{X})/(?P<y>{Y}).(?P<format>png|jpg|jpeg)$'.format(
            DATE=YYYYMMDD,
            ZOOM=ZOOM,
            X=X,
            Y=Y,
        ),
        snodas_tiles.get_tile,
    ),

    # pourpoint geojson (points)
    re_path(
        r'^pourpoints/$',
        pourpoints.get_points,
    ),

    # pourpoint tiles (polygons)
    re_path(
        r'^pourpoints/(?P<zoom>{ZOOM})/(?P<x>{X})/(?P<y>{Y}).mvt$'.format(
            ZOOM=ZOOM,
            X=X,
            Y=Y,
        ),
        pourpoints.get_tile,
    ),

    # snodas stats raw query for data range by pourpoint
    re_path(
        r'^query/pourpoint/(?P<query_type>point|polygon)/(?P<pourpoint_id>{ID})/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
            ID=ID,
            DATE=YYYYMMDD,
        ),
        snodas_stats.get_raw_statistics_pourpoint,
    ),

    # snodas stats raw query for doy by pourpoint
    re_path(
        r'^query/pourpoint/(?P<query_type>polygon)/(?P<pourpoint_id>{ID})/(?P<month>{MM})-(?P<day>{DD})/(?P<start_year>{YYYY})/(?P<end_year>{YYYY})/$'.format(
            ID=ID,
            DD=DD,
            MM=MM,
            YYYY=YYYY,
        ),
        snodas_stats.get_raw_statistics_pourpoint_date,
    ),

    # snodas stat raw query for date range by arbitrary feature
    re_path(
        r'^query/feature/(?P<lat>{LAT})/(?P<long>{LONG})/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
            LAT=LAT,
            LONG=LONG,
            DATE=YYYYMMDD,
        ),
        snodas_stats.get_raw_statistics_feature,
    ),
    # this would be for a post of a geojson feature, but us not yet implemented
    #re_path(
    #    r'^query/feature/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
    #        DATE=YYYYMMDD,
    #    ),
    #    snodas_stats.get_raw_statistics_feature,
    #),

    # old stat query endpoint
    re_path(
        r"^query/(?P<start_year>{Y})/(?P<end_year>{Y})/(?P<month>{M})/(?P<day>{D})/$".format(
            Y=YYYY,
            M=MM,
            D=DD,
        ),
        snodas_stats.get_for_date,
    ),

    # export snodas raster in netcdf for aoi
    #re_path(
    #    r'^export/pourpoint/(?P<pourpoint_id>{ID})/(?P<variable>{SNODAS_VARS})/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
    #        ID=ID,
    #        DATE=YYYYMMDD,
    #        SNODAS_VARS=SNODAS_VARS,
    #    ),
    #   snodas_stats.get_raw_statistics_pourpoint,
    #),

    # streamflow regression query
    re_path(
        r'^analysis/streamflow/(?P<variable>{SNODAS_VARS})/(?P<forecast_start>{MM})/(?P<forecast_end>{MM})/(?P<month>{MM})-(?P<day>{DD})/(?P<start_year>{YYYY})/(?P<end_year>{YYYY})/$'.format(
            SNODAS_VARS=SNODAS_VARS,
            DD=DD,
            MM=MM,
            YYYY=YYYY,
        ),
        snodas_analysis.streamflow_regression,
    ),
]

# standard django url patterns
urlpatterns = [
    # rest urls
    re_path(r'^{}'.format(REST_ROOT), include(rest_urls)),
]

if DEBUG and "debug_toolbar" in INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
