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

    year_range = '[{}, {}]'.format(start_year, end_year)
    month_range = '[{}, {}]'.format(forecast_start, forecast_end)
    query = streamflow.regression(
        variable=variable,
        day=day,
        month=month,
        month_range=month_range,
        year_range=year_range,
        start_month=forecast_start,
        end_month=forecast_end,
        start_year=start_year,
        end_year=end_year,
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
