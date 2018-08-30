from django.conf.urls import include, url

from .settings import REST_ROOT, DEBUG, INSTALLED_APPS

from .views import snodas_tiles, pourpoints, snodas_stats


rest_urls = [
    url(r"^tiles/$", snodas_tiles.list_dates),
    url(r"^tiles/date-params$", snodas_tiles.date_params),
    url(r"^tiles/(?P<year>\d{4})(?P<month>(0[1-9]|1[0-2]))(?P<day>(0[1-9]|[1-2][0-9]|3[0-1]))/(?P<zoom>[0]?[1-9]|1[0-5])/(?P<x>\d+)/(?P<y>\d+).(?P<format>png|jpg|jpeg)$", snodas_tiles.get_tile),
    url(r"^pourpoints/$", pourpoints.get_points),
    url(r"^pourpoints/(?P<zoom>0?[0-9]|1[0-5])/(?P<x>\d+)/(?P<y>\d+).mvt$", pourpoints.get_tile),
    url(r"^query/(?P<start_year>\d{4})/(?P<end_year>\d{4})/(?P<month>(0[1-9]|1[0-2]))/(?P<day>(0[1-9]|[1-2][0-9]|3[0-1]))/$", snodas_stats.get_for_date),
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
