CREATE OR REPLACE FUNCTION pourpoint.bust_cache()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  -- clean out old tiles when pourpoint data changes
  IF TG_OP = 'UPDATE' THEN
    DELETE FROM pourpoint.tile WHERE (
      ST_Intersects(extent, OLD.polygon_simple) OR
      ST_Intersects(extent, NEW.polygon_simple)
    );
  ELSE
    DELETE FROM pourpoint.tile WHERE (
      ST_Intersects(extent, NEW.polygon_simple)
    );
  END IF;
  RETURN NULL;
END;
$$;
