import os

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SnodasConfig(AppConfig):
    name = 'snodas'
    verbose_name = _('SNODAS')

    def ready(self):
        # This ensures we can fully leverage supported parallelism in gdal
        # when running gdal functions by default. It also allows the user
        # to override the amount of parallelism by setting the var themselves.
        if 'GDAL_NUM_THREADS' not in os.environ:
            os.environ['GDAL_NUM_THREADS'] = 'ALL_CPUS'
