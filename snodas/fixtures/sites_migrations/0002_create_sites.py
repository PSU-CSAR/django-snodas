#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings


def insert_sites(apps, schema_editor):
    """Populate the sites model"""
    Site = apps.get_model('sites', 'Site')
    # Register SITE_ID = 1
    site, created = Site.objects.get_or_create(id=1)
    site.domain = settings.SITE_DOMAIN_NAME
    site.name = 'snodas'
    site.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(insert_sites)
    ]
