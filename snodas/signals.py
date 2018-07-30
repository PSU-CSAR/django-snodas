from django.db.backends.postgresql.base import DatabaseWrapper as PostgreSQLDatabaseWrapper
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created, sender=PostgreSQLDatabaseWrapper)
def db_connection_init(sender, connection):
    cmds = connection.settings_dict.get('CONNECTION_INIT', None)

    if cmds:
        if not (isinstance(cmds, list) or isinstance(cmds, tuple)):
            raise TypeError(
                'database CONNECTION_INIT must be tuple or list, found {}'.format(type(cmds))
            )
        with connection.cursor() as cursor:
            for cmd in cmds:
                cursor.execute(cmd)
