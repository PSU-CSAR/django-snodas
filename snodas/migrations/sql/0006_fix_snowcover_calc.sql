CREATE OR REPLACE FUNCTION pourpoint.calc_stats_1(
  p pourpoint.rasterized,
  s snodas.raster
)
RETURNS pourpoint.statistics
LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE
AS $$
BEGIN
  IF NOT p.valid_dates @> s.date THEN
    RAISE EXCEPTION 'SNODAS date not within pourpoint raster valid dates: % not in %',
        s.date,
        p.valid_dates
      USING HINT = 'Make sure you call pourpoint.calc_stats_1 with a valid pourpoint raster for the SNODASdate.';
  END IF;

  IF NOT ST_SameAlignment(p.rast, s.swe) THEN
      RAISE WARNING '%', ST_NotSameAlignmentReason(p.rast, s.swe);
      RAISE WARNING '%', ST_Georeference(p.rast);
      RAISE WARNING '%', ST_Georeference(s.swe);
  END IF;

  RETURN (
    p.rasterized_id,
    p.pourpoint_id,
    s.date,
    -- percent snowcover:
    -- number of cells with data in both rasters
    -- divided by the total number of cells in the
    -- pourpoint raster multiplied by 100
    ST_Count(ST_Reclass(
      ST_MapAlgebra(p.rast, s.swe, '[rast1]*[rast2]', NULL, 'FIRST'),
      1,
      '[-32768-0]:0, (0-32767]:1',
      '1BB',
      0
    ))::float / ST_Count(p.rast) * 100,
    -- snow depth (meters):
    -- average of all cells with data in first
    -- nodata in second counts as 0
    -- scale factor 1000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.depth, '[rast2]/1000', '64BF', 'FIRST', NULL, '0'))).mean,
        -- swe (meters):
    -- average of all cells with data in first
    -- nodata in second counts as 0
    -- scale factor 1000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.swe, '[rast2]/1000', '64BF', 'FIRST', NULL, '0'))).mean,
    -- runoff (meters):
    -- average of all cells with data in first
    -- nodata in second counts as 0
    -- scale factor 100000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.runoff, '[rast2]/100000', '64BF', 'FIRST', NULL, '0'))).mean,
    -- sublimation (meters):
    -- average of all cells with data in first
    -- nodata in second counts as 0
    -- scale factor 100000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.sublimation, '[rast2]/100000', '64BF', 'FIRST', NULL, '0'))).mean,
    -- sublimation_blowing (meters):
    -- average of all cells with data in first
    -- nodata in second counts as 0
    -- scale factor 100000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.sublimation_blowing, '[rast2]/100000', '64BF', 'FIRST', NULL,'0'))).mean,
    -- precip_solid (meters):
    -- average of all cells with data in first
    -- nodata in second counts as 0
    -- scale factor 10
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.precip_solid, '[rast2]/10', '64BF', 'FIRST', NULL, '0'))).mean,
    -- precip_liquid (meters):
    -- average of all cells with data in first
    -- nodata in second counts as 0
    -- scale factor 10
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.precip_liquid, '[rast2]/10', '64BF', 'FIRST', NULL, '0'))).mean,
    -- average_temp (kelvin):
    -- average of all cells with data in both rasters
    -- scale factor 1
    CASE s.average_temp
      WHEN NULL THEN NULL
      ELSE
        (ST_SummaryStats(ST_MapAlgebra(p.rast, s.average_temp, '[rast2]', '64BF', 'FIRST'))).mean
    END
  );
END;
$$;
