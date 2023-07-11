# Useful queries

## How many SNODAS dates are in the database?

To count all the SNODAS dates ingested in the database, run this:

```sql
select
  count(*)
from
  snodas.raster
```

## Finding and fixing missing statistics

To find pourpoints missing statistics, try the following query:

```sql
select
  r.pourpoint_id, count(r.pourpoint_id)
from
  pourpoint.rasterized as r
  cross join snodas.raster as s
  left join pourpoint.statistics as t on t.date = s.date and r.pourpoint_id = t.pourpoint_id
where
  t.pourpoint_id is null
  and r.valid_dates @> s.date
group by
  r.pourpoint_id
;
```

This will show the pourpoints missing statistics, along with the missing dates.

If you want to see the list of missing dates for a given pourpoint, use this
query (subbing in the `pourpoint_id` with the appropriate value):

```sql
select
  s.date
from
  snodas.raster as s
  left join pourpoint.statistics as t using (date)
where
  t.pourpoint_id = <pourpoint_id>
  and t.date is null
;
```

To fill in the missing statistics, something like this will likely work (but
could use some further testing):

```sql
insert into pourpoint.statistics
  select r.*
  from
    pourpoint.rasterized as p, snodas.raster as s
    left join pourpoint.statistics as t on
      t.date = s.date
      and p.pourpoint_id = t.pourpoint_id,
    lateral pourpoint.calc_stats_1((p), (s)) as r
  where
    t.pourpoint_id is null
    and p.valid_dates @> s.date
;
```

## Updating a particular statistic

To see how a statistic is calculated, view the `calc_stats_1` function:

```sql
\sf pourpoint.calc_stats_1
```

To update a statistic, take the relevant calculation from that function and use
it in an update statement, such as the following example that recalculates
percent snow cover for all rows:

```sql
update
  pourpoint.statistics as t
set
  snowcover = ST_Count(ST_Reclass(
      ST_MapAlgebra(p.rast, s.swe, '[rast1]*[rast2]', NULL, 'FIRST'),
      1,
      '[-32768-0]:0, (0-32767]:1',
      '1BB',
      0
    ))::float / ST_Count(p.rast) * 100
from
  pourpoint.rasterized as p,
  snodas.raster as s
where
  p.rasterized_id = t.rasterized_id
  and s.date = t.date
;
```
