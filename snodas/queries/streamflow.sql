--=
SQL for streamflow regression analysis
--=

--- name: regression
--- id: variable
--- param: variable
--- param: month_range
--- param: day
--- param: month
--- param: year_range
--- param: start_month
--- param: end_month
--- param: start_year
--- param: end_year
with
streamflow as (
  select
    awdb_id,
    date_part('year', month) as year,
    sum(acrefeet) as acrefeet
  from streamflow.monthly
  where date_part('month', month)::integer <@ {month_range}::int4range
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
      and {year_range}::int4range @> date_part('year', date)::integer
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
)
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
--- endquery