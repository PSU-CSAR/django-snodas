from django.db import migrations

from snodas.utils.migrations import migration_sql


class Migration(migrations.Migration):
    dependencies = [
        ('snodas', '0003_pourpoint_unique'),
    ]

    operations = [
        migrations.RunSQL(
            migration_sql(__file__),
        ),
    ]
