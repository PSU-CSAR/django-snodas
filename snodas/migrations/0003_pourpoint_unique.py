# -*- coding: utf-8 -*-
import os

from django.db import migrations


with open(
    os.path.join(
        os.path.dirname(__file__),
        'sql',
        os.path.splitext(os.path.basename(__file__))[0] + '.sql',
    )
) as sqlfile:
    sql = sqlfile.read()


class Migration(migrations.Migration):

    dependencies = [
        ('snodas', '0002_streamflow'),
    ]

    operations = [
        migrations.RunSQL(
                sql
            )
    ]
