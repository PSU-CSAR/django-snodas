--=
SQL for streamflow regression analysis
--=

--- name: regression
--- id: variable
--- param: variable
--- param: day
--- param: month
--- raw: start_year
--- raw: end_year
--- raw: start_month
--- raw: end_month
--- raw: streamflow_columns
--- raw: value_columns
with
data as (
  select * from
    crosstab('
      select
        ycpp.awdb_id,
        ycpp.year,
        sm.acrefeet
      from
        (select
           awdb_id,
           year
         from
           (select generate_series({start_year}, {end_year}) as year) y,
           pourpoint.pourpoint pp
        ) as ycpp
        left join (
          select
            awdb_id,
            date_part(''year'', month) as year,
            sum(acrefeet) as acrefeet
          from streamflow.monthly
          where date_part(''month'', month)::integer <@ ''[{start_month}, {end_month}]''::int4range
          group by
            awdb_id,
              date_part(''year'', month)
            having
              every(acrefeet is not null)
        ) as sm using (awdb_id, year)
      order by
        ycpp.awdb_id, ycpp.year
    ') as ct1(
      awdb_id text,
      {streamflow_columns}
    )
    join crosstab('
      select
        ycpp.awdb_id,
        ycpp.year,
        ps.swe as value
      from
        (select
           pp.awdb_id,
           pp.pourpoint_id,
           y.year
         from
           (select generate_series({start_year}, {end_year}) as year) y,
           pourpoint.pourpoint pp
        ) as ycpp
        left join (
          select
            *
          from
            pourpoint.statistics
          where
            date_part(''day'', date) = {day}
              and date_part(''month'', date) = {month}
          ) ps on
          ycpp.pourpoint_id = ps.pourpoint_id
            and ycpp.year = date_part(''year'', ps.date)
      order by
        ycpp.awdb_id, ycpp.year
    ') as ct2(
      awdb_id text,
      {value_columns}
    )
  using (awdb_id)
),
streamflow as (
  select
    awdb_id,
    date_part('year', month) as year,
    sum(acrefeet) as acrefeet
  from streamflow.monthly
  where
    date_part('month', month)::integer <@ '[{start_month}, {end_month}]'::int4range
      and '[{start_year}, {end_year}]'::int4range @> date_part('year', month)::integer
  group by
    awdb_id,
    date_part('year', month)
  having
    every(acrefeet is not null)
),
stats as (
  select
    awdb_id,
    {variable_i} as value,
    date_part('year', date) as year
  from
    pourpoint.statistics
    join pourpoint.pourpoint using (pourpoint_id)
  where
    date_part('day', date) = {day}
      and date_part('month', date) = {month}
      and '[{start_year}, {end_year}]'::int4range @> date_part('year', date)::integer
),
r1 as (
  select
    awdb_id,
    regr_intercept(acrefeet, value) as intercept,
    regr_slope(acrefeet, value) as slope,
    regr_r2(acrefeet, value) as r2,
    regr_count(acrefeet, value) as num_years_included
  from
    stats
    left join streamflow using (awdb_id, year)
  group by awdb_id
),
regression as (
  select
    awdb_id,
    intercept,
    slope,
    r2,
    stddev_pop(acrefeet - (value * slope + intercept)) as std_err_res,
    num_years_included
  from
    stats
    left join streamflow using (awdb_id, year)
    left join r1 using (awdb_id)
  group by awdb_id, intercept, slope, r2, num_years_included
),
aois as (
  select
    p.awdb_id,
    p.name,
    r.intercept,
    r.slope,
    r.r2,
    r.std_err_res,
    {variable} as variable,
    {day} as query_day,
    {month} as query_month,
    {start_month} as start_month,
    {end_month} as end_month,
    {start_year} as start_year,
    {end_year} as end_year,
    num_years_included
  from
    regression r
    join pourpoint.pourpoint p using (awdb_id)
)
select * from
  aois
  left join data using (awdb_id)
--- endquery
