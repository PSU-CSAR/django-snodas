from django.apps import AppConfig, apps
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class SnodasConfig(AppConfig):
    name = 'snodas'
    verbose_name = _("SNODAS")

    def ready(self):
        print settings.MIDDLEWARE
        print [app.verbose_name for app in apps.get_app_configs()]
