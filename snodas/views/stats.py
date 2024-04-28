from io import BytesIO
from typing import assert_never

from django.db import connection
from django.http import HttpResponse

from snodas import types
from snodas.queries import streamflow  # type: ignore
from snodas.utils.http import stream_file


def raw_stat_query_csv(request, cursor, filename, stat_query):
    flike = BytesIO()
    csvquery = (
        f'COPY ({stat_query.as_string(cursor.connection)}) TO STDOUT WITH CSV HEADER'
    )
    cursor.copy_expert(csvquery, flike)

    return stream_file(
        flike,
        filename,
        request,
        'text/csv',
    )


def get_pourpoint_stats(
    pourpoint_id: int,
    query: types.DateQuery,
) -> list[types.SnodasStats]:
    with connection.cursor() as cursor:
        cursor.execute(
            query.stat_query(pourpoint_id).as_string(cursor.connection),
        )
        columns = (x.name for x in cursor.description)
        rows = cursor.fetchall()
        return [
            types.SnodasStats(**dict(zip(columns, row, strict=False))) for row in rows
        ]


def get_csv_statistics(
    request,
    pourpoint_ref: int | str,
    query: types.DateQuery,
):
    if request.method != 'GET':
        return HttpResponse(reason='Not allowed', status=405)

    match pourpoint_ref:
        case int():
            pp_query = """
                SELECT
                    pourpoint_id,
                    name
                FROM
                    pourpoint.pourpoint
                WHERE
                    pourpoint_id = %s
            """
        case str():
            pp_query = """
                SELECT
                    pourpoint_id,
                    name
                FROM
                    pourpoint.pourpoint
                WHERE
                    awdb_id = %s
            """
        case _ as unreachable:
            assert_never(unreachable)

    with connection.cursor() as cursor:
        cursor.execute(pp_query, [pourpoint_ref])
        pp = cursor.fetchone()

        if not pp:
            return HttpResponse(status=404)

        return raw_stat_query_csv(
            request,
            cursor,
            query.csv_name(pp[1]),
            query.stat_query(pp[0]),
        )


def streamflow_regression(
    request,
    variable,
    forecast_start,
    forecast_end,
    month,
    day,
    start_year,
    end_year,
):
    if request.method != 'GET':
        return HttpResponse(reason='Not allowed', status=405)

    forecast_start = int(forecast_start)
    forecast_end = int(forecast_end)
    month = int(month)
    day = int(day)
    start_year = int(start_year)
    end_year = int(end_year)

    streamflow_columns = ', '.join(
        [
            f'streamflow_{year} double precision'
            for year in range(start_year, end_year + 1)
        ],
    )
    value_columns = ', '.join(
        [
            f'{variable}_{year} double precision'
            for year in range(start_year, end_year + 1)
        ],
    )
    query = streamflow.regression(
        variable=variable,
        day=day,
        month=month,
        start_month=forecast_start,
        end_month=forecast_end,
        start_year=start_year,
        end_year=end_year,
        streamflow_columns=streamflow_columns,
        value_columns=value_columns,
    )

    name = (
        f'streamflow_{variable}_{forecast_start}'
        f'-{forecast_end}_{month}-{day}_{start_year}-{end_year}.csv'
    )

    with connection.cursor() as cursor:
        return raw_stat_query_csv(request, cursor, name, query)
