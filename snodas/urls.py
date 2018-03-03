from __future__ import absolute_import

from django.conf.urls import include, url

from .settings import REST_ROOT, DEBUG, INSTALLED_APPS


rest_urls = [

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
