from django.db import migrations

from snodas.utils.migrations import migration_sql


class Migration(migrations.Migration):
    dependencies = [
        ('snodas', '0004_fix_bust_cache'),
    ]

    operations = [
        migrations.RunSQL(
            migration_sql(__file__),
        ),
    ]
