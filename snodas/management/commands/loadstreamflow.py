# based in part on the loaddata command from django
# some of the code falls under that django copyright
import datetime
import json

from pprint import pprint

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from psycopg2.extras import execute_values

from snodas.management import utils


class Command(BaseCommand):
    help = (
        'Load the specified json file(s) with monthly streamflow '
        'aggregate data into the database. '
        'Each /file will run within a separate transaction.'
    )
    missing_args_message = (
        'No json file specified. Please provide the path of at least '
        'one json file in the command line.'
    )

    requires_system_checks = []  # type: ignore  # noqa: RUF012

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            'args',
            metavar='jsonfiles',
            type=utils.file,
            nargs='+',
            help='json files to import. Can also use - to pass commands via stdin.',
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help=(
                'Specify a specific database to load data into. '
                'Defaults to the "default" database.',
            ),
        )
        parser.add_argument(
            '--no-transaction',
            dest='use_transaction',
            action='store_false',
            help='Do not execute imports inside transactions. Default false.',
        )

    def handle(self, *jsonfiles, **options):
        self.verbosity = options['verbosity']
        db = options['database']
        self.conn = connections[db]

        for jsonfile in jsonfiles:
            self.vprint(2, f'Processing file {jsonfile}...')

            self.vprint(2, '...opening file...')
            with jsonfile.open('r') as f:
                _json = json.load(f)
            self.vprint(2, 'File opened.')

            self.vprint(2, 'Importing json...')
            if options['use_transaction']:
                with transaction.atomic(using=db):
                    self.vprint(
                        2,
                        '...opened transaction...',
                    )
                    self.import_json(_json)

            else:
                self.import_json(_json)
            self.vprint(2, 'import completed.')

        # Close the DB connection -- unless we're still in a transaction. This
        # is required as a workaround for an edge case in MySQL: if the same
        # connection is used to create tables, load data, and query, the query
        # can return incorrect results. See Django #7572, MySQL #37735.
        if transaction.get_autocommit(db):
            self.conn.close()

    @staticmethod
    def _iter_month(date):
        yield date
        while True:
            month = (date.month % 12) + 1
            year = date.year + (date.month + 1 > 12)
            date = datetime.date(year, month, 1)
            yield date

    def _vals_to_records(self, start, awdb_id, values):
        return [
            (awdb_id, date, val)
            for date, val in zip(self._iter_month(start), values, strict=False)
        ]

    def _parse_json(self, json):
        if json['duration'] != 'MONTHLY':
            raise CommandError('Data does not look like monthly streamflow data')
        start = datetime.datetime.strptime(
            json['beginDate'],
            '%Y-%m-%d %H:%M:%S',
        ).astimezone(datetime.UTC).date()
        awdb_id = json['stationTriplet']
        return self._vals_to_records(start, awdb_id, json['values'])

    def import_json(self, json):
        records = self._parse_json(json)
        insert_sql = """
INSERT INTO streamflow.monthly (awdb_id, month, acrefeet)
VALUES %s
ON CONFLICT (awdb_id, month) DO UPDATE SET
   (awdb_id, month, acrefeet) = (EXCLUDED.awdb_id, EXCLUDED.month, EXCLUDED.acrefeet)
"""
        with self.conn.cursor() as cur:
            execute_values(cur, insert_sql, records)
        self.vprint(1, f'loaded {len(records)} records for {records[0][0]}')

    def vprint(self, level, *args, **kwargs):
        _print = print
        if kwargs.pop('pretty', False):
            _print = pprint
        if self.verbosity >= level:
            _print(*args, **kwargs)
