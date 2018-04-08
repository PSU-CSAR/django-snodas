from __future__ import absolute_import

from django.conf.urls import include, url

from .settings import REST_ROOT, DEBUG, INSTALLED_APPS

from . import views

rest_urls = [
    url(r"^tiles/$", views.list_tiles),
    url(r"^tiles/(?P<date>\d{4}-\d{2}-\d{2})/(?P<zoom>\d{1,2})/(?P<x>\d+)/(?P<y>\d+).(?P<format>png|jpg|jpeg)$", views.get_tile),
    url(r"^query/(?P<start_year>\d{4})/(?P<end_year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$", views.get_stats_date),
    url(r"^query/(?P<start_year>\d{4})/(?P<end_year>\d{4})/(?P<doy>\d{1-3})/$", views.get_stats_doy),
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
