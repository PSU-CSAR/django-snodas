from io import BytesIO

from django.db import connection
from django.http import HttpResponse

from ..utils.http import stream_file
from ..queries import streamflow


def raw_stat_query(request, cursor, filename, stat_query):
    flike = BytesIO()
    csvquery = "COPY ({}) TO STDOUT WITH CSV HEADER".format(
        stat_query.as_string(cursor.connection)
    )
    cursor.copy_expert(csvquery, flike)

    return stream_file(
            flike,
            filename,
            request,
            'text/csv',
        )


def streamflow_regression(request, variable, forecast_start, forecast_end,
                          month, day, start_year, end_year, name=None):
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

    with connection.cursor() as cursor:
        if not name:
            name = 'streamflow_{}_{}-{}_{}-{}_{}-{}.csv'.format(
                    variable,
                    forecast_start,
                    forecast_end,
                    month,
                    day,
                    start_year,
                    end_year,
                )

        return raw_stat_query(request, cursor, name, query)
