from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from django.db.utils import Error


class SnodasConfig(AppConfig):
    name = 'snodas'
    verbose_name = _("SNODAS")

    def ready(self):
        import snodas.signals
