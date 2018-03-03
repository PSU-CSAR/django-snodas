from __future__ import absolute_import, print_function

from getpass import getpass

from psycopg2 import connect, ProgrammingError
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError

from ..utils import get_default

from . import dropdb


class Command(BaseCommand):
    help = """Creates a postgresql database for snodas using the
    settings defined for the current instance of the project."""

    requires_system_checks = False
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
            '--create-superuser',
            action='store_false',
            help='Make the created DB user a superuser. '
                 'Default is false, unless ENV is development.',
        )
        parser.add_argument(
            '--template',
            default='postgis_21',
            help='An existing database template to use. '
                 'Default is "postgis_21".',
        )
        parser.add_argument(
            '--tablespace',
            default='gis_data',
            help='An existing tablespace to use. '
                 'Default is "gis_data"',
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

    def handle(self, *args, **options):
        router = options.get('router')
        dbinfo = settings.DATABASES.get(router)
        if dbinfo is None:
            raise CommandError("Unknown database router %s" % router)

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
            management.call_command(dropdb.Command(router=router))

        con = None
        con = connect(dbname='postgres',
                      user=createuser,
                      password=createpass,
                      host=dbhost,
                      port=dbport)

        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()

        try:
            cur.execute("CREATE USER {} WITH ENCRYPTED PASSWORD '{}' CREATEDB;".format(dbuser, dbpass))
        except ProgrammingError:
            pass
        else:
            if options.get('create_superuser') or \
                    settings.ENV == 'development':
                cur.execute('ALTER ROLE {} SUPERUSER'.format(dbuser))

        cur.execute('CREATE DATABASE {} WITH ENCODING \'UTF-8\' OWNER {} TEMPLATE {} TABLESPACE {};'.format(dbname, dbuser, options['template'], options['tablespace']))
        cur.execute('GRANT ALL PRIVILEGES ON DATABASE {} TO {};'.format(dbname, dbuser))
        cur.close()
        con.close()

        print((
            '\nDatabase {} created. '
            'Be sure to run the data migrations:\n\n'
            '`snodas migrate [options]`'
        ).format(settings.INSTANCE_NAME))
