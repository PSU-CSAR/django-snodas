from django.conf.urls import include, url

from .settings import REST_ROOT, DEBUG, INSTALLED_APPS

from .views import snodas_tiles, pourpoints, snodas_stats


rest_urls = [
    url(r"^tiles/$", snodas_tiles.list_dates),
    url(r"^tiles/(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})/(?P<zoom>[0]?[1-9]|1[0-5])/(?P<x>\d+)/(?P<y>\d+).(?P<format>png|jpg|jpeg)$", snodas_tiles.get_tile),
    url(r"^pourpoints/$", pourpoints.get_points),
    url(r"^pourpoints/(?P<zoom>\d{1,2})/(?P<x>\d+)/(?P<y>\d+).mvt$", pourpoints.get_tile),
    url(r"^query/(?P<start_year>\d{4})/(?P<end_year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$", snodas_stats.get_for_date),
    url(r"^query/(?P<start_year>\d{4})/(?P<end_year>\d{4})/(?P<doy>\d{1-3})/$", snodas_stats.get_for_doy),
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
