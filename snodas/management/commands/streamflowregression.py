from argparse import Namespace

from django.core.management.base import BaseCommand
from django.db import connection

from snodas.constants import snodas_variables
from snodas.queries import streamflow  # type: ignore


def print_dict_table(my_dict, col_list=None) -> None:
    """Pretty print a list of dictionaries (myDict) as a
    dynamically sized table. If column names (colList)
    aren't specified, they will show in random order.
    Author: Thierry Husson - Use it as you want but don't blame me.
    From: https://stackoverflow.com/a/40389411/2864991"""
    if not col_list:
        col_list = list(my_dict[0].keys() if my_dict else [])

    # make header
    my_list = [col_list]

    for item in my_dict:
        my_list.append([f'{item[col]}' for col in col_list])

    col_size = [max(map(len, col)) for col in zip(*my_list, strict=False)]
    format_str = ' | '.join([f'{{:<{i}}}' for i in col_size])
    my_list.insert(1, ['-' * i for i in col_size])

    for item in my_list:
        print(format_str.format(*item))  # noqa: T201


class Command(BaseCommand):
    help = """Run a regression analysis to compare a
    SNODAS variable on a given date to streamflow."""

    requires_system_checks = []  # type: ignore  # noqa: RUF012
    can_import_settings = True

    cols = snodas_variables

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
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
        streamflow_columns = ', '.join(
            [
                f'streamflow_{year} double precision'
                for year in range(self.options.start_year, self.options.end_year + 1)
            ],
        )
        value_columns = ', '.join(
            [
                f'{self.options.variable}_{year} double precision'
                for year in range(self.options.start_year, self.options.end_year + 1)
            ],
        )
        query = streamflow.regression(
            variable=self.options.variable,
            day=self.options.day,
            month=self.options.month,
            start_month=self.options.start_month,
            end_month=self.options.end_month,
            start_year=self.options.start_year,
            end_year=self.options.end_year,
            streamflow_columns=streamflow_columns,
            value_columns=value_columns,
        )

        with connection.cursor() as cursor:
            cursor.execute(query)
            self.query_cols = [c.name for c in cursor.description]
            return [
                dict(zip(self.query_cols, row, strict=False))
                for row in cursor.fetchall()
            ]

    def handle(self, *_, **options) -> None:
        self.options = Namespace(**options)
        result = self.run_query()
        print_dict_table(result, self.query_cols)
