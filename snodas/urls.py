from django.conf.urls import include, url

from .settings import REST_ROOT, DEBUG, INSTALLED_APPS

from .views import snodas_tiles, pourpoints, snodas_stats


# url regex patterns
YYYY = r'\d{4}'
MM = r'(0[1-9]|1[0-2])'
DD = r'(0[1-9]|[1-2][0-9]|3[0-1])'
YYYYMMDD = r'{YYYY}{MM}{DD}'.format(YYYY=YYYY, MM=MM, DD=DD)
ZOOM = r'[0]?[1-9]|1[0-5]'
X = r'\d+'
Y = r'\d+'
ID = r'\d+'

rest_urls = [
    url(
        r'^tiles/$',
        snodas_tiles.list_dates,
    ),
    url(
        r'^tiles/date-params$',
        snodas_tiles.date_params,
    ),
    url(
        r'^tiles/(?P<date>{DATE})/(?P<zoom>{ZOOM})/(?P<x>{X})/(?P<y>{Y}).(?P<format>png|jpg|jpeg)$'.format(
            DATE=YYYYMMDD,
            ZOOM=ZOOM,
            X=X,
            Y=Y,
        ),
        snodas_tiles.get_tile,
    ),
    url(
        r'^pourpoints/$',
        pourpoints.get_points,
    ),
    url(
        r'^pourpoints/(?P<zoom>{ZOOM})/(?P<x>{X})/(?P<y>{Y}).mvt$'.format(
            ZOOM=ZOOM,
            X=X,
            Y=Y,
        ),
        pourpoints.get_tile,
    ),
    url(
        r'^query/(?P<pourpoint_id>{ID})/(?P<start_date>{DATE})/(?P<end_date>{DATE})/$'.format(
            ID=ID,
            DATE=YYYYMMDD,
        ),
    snodas_stats.get_raw_statistics_pourpoint,
    ),
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
