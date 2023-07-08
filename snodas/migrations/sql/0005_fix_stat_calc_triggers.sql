-- trigger on insert/update of pourpoint geom
-- to make pixel join table entries with areas
CREATE OR REPLACE FUNCTION pourpoint.rasterize()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  -- if update delete existing rasterization
  -- cascade will also delete any statistics
  DELETE FROM pourpoint.rasterized
    WHERE pourpoint_id = NEW.pourpoint_id;

  IF NEW.polygon IS NULL THEN
    RETURN NULL;
  END IF;

  -- create a new rasterization
  INSERT INTO pourpoint.rasterized (
    pourpoint_id,
    valid_dates,
    rast,
    area_meters
  ) SELECT
      NEW.pourpoint_id,
      s.valid_dates,
      pourpoint.rasterize_1((NEW), (s)),
      NEW.area_meters
    FROM snodas.geotransform as s;

  RETURN NULL;
END;
$$;


CREATE OR REPLACE FUNCTION pourpoint.calc_stats()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  -- if update deletes existing rasterization
  -- cascade will also delete any statistics

  -- calc the pourpoint stats for all snodas dates
  INSERT INTO pourpoint.statistics
    SELECT r.*
    FROM
      snodas.raster as s,
      pourpoint.calc_stats_1((NEW), (s)) as r
    WHERE
      NEW.valid_dates @> s.date;

  RETURN NULL;
END;
$$;


CREATE OR REPLACE TRIGGER pourpoint_update_rasterize
AFTER UPDATE ON pourpoint.pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon
) EXECUTE PROCEDURE pourpoint.rasterize();

-- we calc stats on the raster, so we don't really care
-- about the pourpoint record itself when triggering
DROP TRIGGER pourpoint_insert_calc_stats ON pourpoint.pourpoint;
DROP TRIGGER pourpoint_update_calc_stats ON pourpoint.pourpoint;

CREATE OR REPLACE TRIGGER pourpoint_insert_calc_stats
AFTER INSERT ON pourpoint.rasterized
FOR EACH ROW EXECUTE PROCEDURE pourpoint.calc_stats();
