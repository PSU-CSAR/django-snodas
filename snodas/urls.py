from django.conf.urls import include, url

from .settings import REST_ROOT, DEBUG, INSTALLED_APPS

from .views import snodas_tiles, pourpoints, snodas_stats


# TODO: change these to be django url convertors
# see https://docs.djangoproject.com/en/2.1/topics/http/urls/#registering-custom-path-converters
# url regex patterns
LAT = r'(\+|-)?(?:90(?:(?:\.0*)?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]*)?))'
LONG = r'(\+|-)?(?:180(?:(?:\.0*)?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]*)?))'
YYYY = r'\d{4}'
MM = r'(0[1-9]|1[0-2])'
DD = r'(0[1-9]|[1-2][0-9]|3[0-1])'
YYYYMMDD = r'{YYYY}-?{MM}-?{DD}'.format(YYYY=YYYY, MM=MM, DD=DD)
ZOOM = r'[0]?[1-9]|1[0-5]'
X = r'\d+'
Y = r'\d+'
ID = r'\d+'

rest_urls = [
    # find all snodas dates
    url(
        r'^tiles/$',
        snodas_tiles.list_dates,
    ),

    # snodas start, end, and missing dates (legacy)
    url(
        r'^tiles/date-params$',
        snodas_tiles.date_params,
    ),

    # snodas raster tiles by date
    url(
        r'^tiles/(?P<date>{DATE})/(?P<zoom>{ZOOM})/(?P<x>{X})/(?P<y>{Y}).(?P<format>png|jpg|jpeg)$'.format(
            DATE=YYYYMMDD,
            ZOOM=ZOOM,
            X=X,
            Y=Y,
        ),
        snodas_tiles.get_tile,
    ),

    # pourpoint geojson (points)
    url(
        r'^pourpoints/$',
        pourpoints.get_points,
    ),

    # pourpoint tiles (polygons)
    url(
        r'^pourpoints/(?P<zoom>{ZOOM})/(?P<x>{X})/(?P<y>{Y}).mvt$'.format(
            ZOOM=ZOOM,
            X=X,
            Y=Y,
        ),
        pourpoints.get_tile,
    ),

    # snodas stats raw query for data range by pourpoint
    url(
        r'^query/pourpoint/(?P<query_type>point|polygon)/(?P<pourpoint_id>{ID})/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
            ID=ID,
            DATE=YYYYMMDD,
        ),
    snodas_stats.get_raw_statistics_pourpoint,
    ),

    # snodas stat raw query for date range by arbitrary feature
    url(
        r'^query/feature/(?P<lat>{LAT})/(?P<long>{LONG})/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
            LAT=LAT,
            LONG=LONG,
            DATE=YYYYMMDD,
        ),
        snodas_stats.get_raw_statistics_feature,
    ),
    # this would be for a post of a geojson feature, but us not yet implemented
    #url(
    #    r'^query/feature/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
    #        DATE=YYYYMMDD,
    #    ),
    #    snodas_stats.get_raw_statistics_feature,
    #),

    # old stat query endpoint
    url(
        r"^query/(?P<start_year>{Y})/(?P<end_year>{Y})/(?P<month>{M})/(?P<day>{D})/$".format(
            Y=YYYY,
            M=MM,
            D=DD,
        ),
        snodas_stats.get_for_date,
    ),
]

# standard django url patterns
urlpatterns = [
    # rest urls
    url(r'^{}'.format(REST_ROOT), include(rest_urls)),
]

if DEBUG and "debug_toolbar" in INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
