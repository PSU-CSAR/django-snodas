# based in part on the loaddata command from django
# some of the code falls under that django copyright
import gzip
import os
import sys
from pprint import pprint
from zipfile import ZipFile

import sqlparse
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction

try:
    import bz2

    has_bz2 = True
except ImportError:
    has_bz2 = False


READ_STDIN = '-'


class SingleZipReader(ZipFile):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(self.namelist()) != 1:
            raise ValueError('Zip-compressed sql must contain only one file.')

    def read(self):
        return super().read(self, self.namelist()[0])


class Command(BaseCommand):
    help = (
        'Run specified sql file(s) against the database. '
        'Each sql command/file will run within a separate transaction.'
    )
    missing_args_message = (
        'No sql file specified. Please provide the path of at least '
        'one sql file in the command line.'
    )

    readers = {
        None: (open, 'rb'),
        '.sql': (open, 'rb'),
        '.gz': (gzip.GzipFile, 'rb'),
        '.zip': (SingleZipReader, 'r'),
        'stdin': (lambda *args: sys.stdin, None),
    }
    if has_bz2:
        readers['.bz2'] = (bz2.BZ2File, 'r')

    requires_system_checks = []

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            'args',
            metavar='sqlfiles',
            nargs='+',
            help='sql files to execute. Can also use - to pass commands via stdin.',
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Nominates a specific database to load fixtures into. Defaults to the "default" database.',
        )
        parser.add_argument(
            '--no-transaction',
            dest='use_transaction',
            action='store_false',
            help='Do not execute sql in transactions. Default false.',
        )

    def handle(self, *sqlfiles, **options):
        self.verbosity = options['verbosity']
        db = options['database']
        self.conn = connections[db]
        sf_readers = {sf: self.get_reader(sf) for sf in sqlfiles}

        for sqlfile, reader in sf_readers.items():
            self.vprint(2, f'Processing file {sqlfile}...')

            self.vprint(2, '...opening file...')
            opener, mode = reader
            self.vprint(3, f'...using reader {opener}...')
            with opener(sqlfile, mode) as s:
                sql = s.read()
            self.vprint(2, 'File opened.')

            self.vprint(2, 'Running sql...')
            if options['use_transaction']:
                with transaction.atomic(using=db):
                    self.vprint(
                        2,
                        '...opened transaction...',
                    )
                    self.runsql(sql)

            else:
                self.runsql(sql)
            self.vprint(2, 'sql completed.')

        # Close the DB connection -- unless we're still in a transaction. This
        # is required as a workaround for an edge case in MySQL: if the same
        # connection is used to create tables, load data, and query, the query
        # can return incorrect results. See Django #7572, MySQL #37735.
        if transaction.get_autocommit(db):
            self.conn.close()

    def runsql(self, sql):
        for statement in sqlparse.split(sql):
            if not statement:
                continue
            self.vprint(3, statement, pretty=True)
            with self.conn.cursor() as cur:
                cur.execute(statement)
                try:
                    self.vprint(1, cur.fetchall(), pretty=True)
                except:
                    self.vprint(1, cur.statusmessage)

    def vprint(self, level, *args, **kwargs):
        _print = print
        if kwargs.pop('pretty', False):
            _print = pprint
        if self.verbosity >= level:
            _print(*args, **kwargs)

    def get_reader(self, sqlfile):
        """
        Return file reader for file format per sqlfile name.
        """
        if sqlfile == READ_STDIN:
            return self.readers['stdin']

        if not os.path.isfile(sqlfile):
            raise CommandError(
                f'sql file {sqlfile} could not be found',
            )

        try:
            return self.readers[os.path.splitext(sqlfile)[1]]
        except KeyError:
            raise CommandError(
                f'sql file {sqlfile} is not a known format.',
            )
