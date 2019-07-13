from argparse import Namespace

from django.db import connection
from django.core.management.base import BaseCommand

from ...constants import snodas_variables
from ...queries import streamflow


def print_dict_table(my_dict, col_list=None):
    '''Pretty print a list of dictionaries (myDict) as a
    dynamically sized table. If column names (colList)
    aren't specified, they will show in random order.
    Author: Thierry Husson - Use it as you want but don't blame me.
    From: https://stackoverflow.com/a/40389411/2864991'''
    if not col_list:
        col_list = list(my_dict[0].keys() if my_dict else [])

    # make header
    my_list = [col_list]

    for item in my_dict:
        my_list.append(['{}'.format(item[col]) for col in col_list])

    col_size = [max(map(len, col)) for col in zip(*my_list)]
    format_str = ' | '.join(["{{:<{}}}".format(i) for i in col_size])
    my_list.insert(1, ['-' * i for i in col_size])

    for item in my_list:
        print(format_str.format(*item))


class Command(BaseCommand):
    help = """Run a regression analysis to compare a
    SNODAS variable on a given date to streamflow."""

    requires_system_checks = False
    can_import_settings = True

    cols = snodas_variables

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-m',
            '--variable',
            choices=self.cols,
            required=True,
            help='SNODAS variable to query.',
        )
        parser.add_argument(
            '-s',
            '--start-year',
            type=int,
            required=True,
            help='Start date of query. Format YYYY.',
        )
        parser.add_argument(
            '-e',
            '--end-year',
            type=int,
            required=True,
            help='End date of query. Format YYYY.',
        )
        parser.add_argument(
            '-d',
            '--day',
            type=int,
            required=True,
            help='Day of variable sample date, e.g., for Feb 23, use 23',
        )
        parser.add_argument(
            '-M',
            '--month',
            type=int,
            required=True,
            help='Month of variable sample date, e.g., for Feb 23, use 2',
        )
        parser.add_argument(
            '-S',
            '--start-month',
            type=int,
            required=True,
            help='Start month of streamflow as number, e.g., April is 4.',
        )
        parser.add_argument(
            '-E',
            '--end-month',
            type=int,
            required=True,
            help='End month of streamflow as number, e.g., July is 7.',
        )

    def run_query(self):
        year_range = '[{}, {}]'.format(
            self.options.start_year, self.options.end_year)
        month_range = '[{}, {}]'.format(
            self.options.start_month, self.options.end_month)
        query = streamflow.regression(
            variable=self.options.variable,
            day=self.options.day,
            month=self.options.month,
            month_range=month_range,
            year_range=year_range,
            start_month=self.options.start_month,
            end_month=self.options.end_month,
            start_year=self.options.start_year,
            end_year=self.options.end_year,
        )

        with connection.cursor() as cursor:
            cursor.execute(query)
            self.query_cols = [c.name for c in cursor.description]
            return [
                dict(zip(self.query_cols, row))
                for row in cursor.fetchall()
            ]

    def handle(self, *args, **options):
        self.options = Namespace(**options)
        result = self.run_query()
        print_dict_table(result, self.query_cols)
