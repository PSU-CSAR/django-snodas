import os
import sys

from getpass import getpass

from psycopg2 import connect, ProgrammingError

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError

from ..utils import get_default

from . import dropdb


class Command(BaseCommand):
    help = """Creates a postgresql database for using the
    settings defined for the current instance of the project."""

    requires_system_checks = []
    can_import_settings = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-U',
            '--admin-user',
            default='postgres',
            help='The admin postgres user to use to create the DB. '
                 'Default is postgres.',
        )
        parser.add_argument(
            '-P',
            '--admin-pass',
            help='The admin postgres user to use to create the DB. '
                 'Default is to prompt user for input.',
        )
        parser.add_argument(
            '-R',
            '--router',
            action='store',
            default='default',
            help='Use this router-database other than '
                 'the default defined in settings.py',
        )
        parser.add_argument(
            '-D',
            '--drop',
            action='store_true',
            default=False,
            help='If given, the database will be dropped before creation.',
        )
        parser.add_argument(
            '-o',
            '--owner',
            default='app',
            help='The database owner username.'
        )

    def handle(self, *args, **options):
        router = options.get('router')
        dbinfo = settings.DATABASES.get(router)
        if dbinfo is None:
            raise CommandError("Unknown database router %s" % router)

        owner = options.get('owner')
        createuser = options.get('admin_user')
        createpass = get_default(
            options,
            'admin_pass',
            getpass('Please enter the {} user password: '.format(createuser)),
        )

        dbuser = dbinfo.get('USER')
        dbpass = dbinfo.get('PASSWORD')
        dbname = dbinfo.get('NAME')
        dbhost = get_default(dbinfo, 'HOST', 'localhost')
        dbport = get_default(dbinfo, 'PORT', 5432)

        if options.get('drop', None):
            management.call_command(
                dropdb.Command(),
                router=router,
                admin_user=createuser,
                admin_pass=createpass,
            )

        try:
            connection = connect(
                dbname='postgres',
                user=createuser,
                password=createpass,
                host=dbhost,
                port=dbport,
            )
            connection.autocommit = True
            with connection.cursor() as cursor:
                # create the owner role for consistent object ownership
                try:
                    cursor.execute("CREATE ROLE {}".format(owner))
                except ProgrammingError:
                    # app user already exists
                    pass

                # create the login user
                try:
                    cursor.execute(
                        "CREATE ROLE {} WITH LOGIN ENCRYPTED PASSWORD '{}' IN ROLE {}".format(
                            dbuser,
                            dbpass,
                            owner,
                        ),
                    )
                except ProgrammingError:
                    # login user already exsits
                    pass

                # create the database
                cursor.execute(
                    'CREATE DATABASE {} WITH ENCODING \'UTF-8\' OWNER {}'.format(
                        dbname,
                        owner,
                    ),
                )
        finally:
            try:
                connection.close()
            except (NameError, AttributeError):
                pass

        try:
            connection = connect(
                dbname=dbname,
                user=createuser,
                password=createpass,
                host=dbhost,
                port=dbport,
            )
            connection.autocommit = True
            with connection.cursor() as cursor:
                # let's add the extenions that require superuser permissions
                # pg_tms cascade tries to setup postgis, but doesn't work with >=3.x
                # so we explicitly install the raster extension as a workaround
                cursor.execute('CREATE EXTENSION postgis_raster CASCADE')
                cursor.execute('CREATE EXTENSION pg_tms CASCADE')
                cursor.execute('CREATE EXTENSION btree_gist')
                cursor.execute('CREATE EXTENSION tablefunc')
        finally:
            try:
                connection.close()
            except (NameError, AttributeError):
                pass

        print((
            '\nDatabase {} created. '
            'Be sure to run the data migrations:\n\n'
            '`{} migrate [options]`'
        ).format(settings.PROJECT_NAME, os.path.basename(sys.argv[0])))
