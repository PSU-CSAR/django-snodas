from io import BytesIO
from typing import assert_never

from django.db import connection
from django.http import HttpResponse

from snodas import types
from snodas.utils.http import stream_file
from snodas.queries import streamflow


def raw_stat_query_csv(request, cursor, filename, stat_query):
    flike = BytesIO()
    csvquery = 'COPY ({}) TO STDOUT WITH CSV HEADER'.format(
        stat_query.as_string(cursor.connection),
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
) -> dict[str, types.SnodasStats]:
    with connection.cursor() as cursor:
        cursor.execute(
            query.stat_query(pourpoint_id).as_string(cursor.connection),
        )
        columns = (x.name for x in cursor.description)
        rows = cursor.fetchall()
        rtn: dict[str, types.SnodasStats] = {}

        for row in rows:
            result = dict(zip(columns, row))
            date = result.pop('date')
            rtn[str(date)] = types.SnodasStats(**result)

        return rtn


def get_csv_statistics(
    request,
    pourpoint_ref: int | str,
    query: types.DateQuery,
):
    if request.method != 'GET':
        return HttpResponse(reason="Not allowed", status=405)

    match pourpoint_ref:
        case int():
            pp_query = '''
                SELECT
                    pourpoint_id,
                    name
                FROM
                    pourpoint.pourpoint
                WHERE
                    pourpoint_id = %s
            '''
        case str():
            pp_query = '''
                SELECT
                    pourpoint_id,
                    name
                FROM
                    pourpoint.pourpoint
                WHERE
                    awdb_id = %s
            '''
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
        return HttpResponse(reason="Not allowed", status=405)

    forecast_start = int(forecast_start)
    forecast_end = int(forecast_end)
    month = int(month)
    day = int(day)
    start_year = int(start_year)
    end_year = int(end_year)

    streamflow_columns = ', '.join(
        ['streamflow_{} double precision'.format(year)
         for year in range(start_year, end_year+1)]
    )
    value_columns = ', '.join(
        ['{}_{} double precision'.format(variable, year)
         for year in range(start_year, end_year+1)]
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

    name = 'streamflow_{}_{}-{}_{}-{}_{}-{}.csv'.format(
            variable,
            forecast_start,
            forecast_end,
            month,
            day,
            start_year,
            end_year,
        )

    with connection.cursor() as cursor:
        return raw_stat_query_csv(request, cursor, name, query)
