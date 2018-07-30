from __future__ import absolute_import

from getpass import getpass

from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from six.moves import input

from ..utils import get_default


class Command(BaseCommand):
    help = """Drops a postgresql database for this snodas instance using
    the settings defined for the current instance of the project."""

    requires_system_checks = False
    can_import_settings = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--drop-user',
            action='store_true',
            help='Drop the DB user for the project. '
                 'Requires that admin user and password be specified.',
        )
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
            '--noinput',
            action='store_false',
            dest='interactive',
            default=True,
            help='Tells Django to NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            '-R',
            '--router',
            action='store',
            default='default',
            help='Use this router-database other than '
                 'the default defined in settings.py',
        )

    def handle(self, *args, **options):
        if settings.ENV == 'production':
            raise CommandError('I won\'t run on a production database. Sorry.')

        router = options.get('router')
        dbinfo = settings.DATABASES.get(router)
        if dbinfo is None:
            raise CommandError('Unknown database router {}'.format(router))

        dbuser = dbinfo.get('USER')
        dbpass = dbinfo.get('PASSWORD')

        if options.get('drop_user'):
            dbuser = options.get('admin_user')
            dbpass = get_default(
                options,
                'admin_pass',
                getpass('Please enter the {} user password: '.format(dbuser)),
            )

        dbname = dbinfo.get('NAME')
        dbhost = get_default(dbinfo, 'HOST', 'localhost')
        dbport = get_default(dbinfo, 'PORT', 5432)

        if options.get('interactive'):
            confirm = input(
                ('You have requested to drop the database.\n'
                 'This will IRREVERSIBLY DESTROY\n'
                 'ALL data in the database "{}".\n'
                 'Are you sure you want to do this?\n'
                 'Type "yes" to continue, or "no" to cancel: ').format(dbname))
        else:
            confirm = 'yes'

        if confirm != 'yes':
            print('Drop cancelled.')
            return

        # need to make sure we're not connected to the DB?
        connection.close()

        with connect(
            dbname='postgres',
            user=dbuser,
            password=dbpass,
            host=dbhost,
            port=dbport,
        ) as conn:
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute('DROP DATABASE IF EXISTS {}'.format(dbname))

            if options.get('drop_user'):
                cursor.execute('DROP USER IF EXISTS {}'.format(dbinfo.get('USER')))
