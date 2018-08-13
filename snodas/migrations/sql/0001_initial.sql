-- this file should be run as the 'app' user
-- so the 'app' user becomes the owner of all

-------------------------------------------------------------------
-- extensions (added elsewhere, requires superuser permissions)
-------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_tms CASCADE;
CREATE EXTENSION IF NOT EXISTS btree_gist;


--------------
-- schemas
--------------
CREATE SCHEMA snodas;
CREATE SCHEMA pourpoint;


---------------
--  generic
---------------

CREATE OR REPLACE FUNCTION pourpoint.calc_polygon_area()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  NEW.area_meters = ST_Area(NEW.polygon::geography);
  RETURN NEW;
END;
$$;


---------------
--  SNODAS
---------------

CREATE TABLE snodas.raster (
  "swe" raster NOT NULL,
  "depth" raster NOT NULL,
  "runoff" raster NOT NULL,
  "sublimation" raster NOT NULL,
  "sublimation_blowing" raster NOT NULL,
  "precip_solid" raster NOT NULL,
  "precip_liquid" raster NOT NULL,
  "average_temp" raster NOT NULL,
  "date" date NOT NULL PRIMARY KEY,
  -- swe constraints
  CONSTRAINT enforce_height_swe CHECK (st_height(swe) = 3351),
  CONSTRAINT enforce_nodata_values_swe CHECK (_raster_constraint_nodata_values(swe)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_swe CHECK (st_numbands(swe) = 1),
  CONSTRAINT enforce_out_db_swe CHECK (_raster_constraint_out_db(swe) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_swe CHECK (_raster_constraint_pixel_types(swe) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_swe CHECK (st_scalex(swe)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_swe CHECK (st_scaley(swe)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10)),
  -- depth constraints
  CONSTRAINT enforce_height_depth CHECK (st_height(depth) = 3351),
  CONSTRAINT enforce_nodata_values_depth CHECK (_raster_constraint_nodata_values(depth)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_depth CHECK (st_numbands(depth) = 1),
  CONSTRAINT enforce_out_db_depth CHECK (_raster_constraint_out_db(depth) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_depth CHECK (_raster_constraint_pixel_types(depth) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_depth CHECK (st_scalex(depth)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_depth CHECK (st_scaley(depth)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10)),
  -- runoff constraints
  CONSTRAINT enforce_height_runoff CHECK (st_height(runoff) = 3351),
  CONSTRAINT enforce_nodata_values_runoff CHECK (_raster_constraint_nodata_values(runoff)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_runoff CHECK (st_numbands(runoff) = 1),
  CONSTRAINT enforce_out_db_runoff CHECK (_raster_constraint_out_db(runoff) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_runoff CHECK (_raster_constraint_pixel_types(runoff) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_runoff CHECK (st_scalex(runoff)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_runoff CHECK (st_scaley(runoff)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10)),
  -- sublimation constraints
  CONSTRAINT enforce_height_sublimation CHECK (st_height(sublimation) = 3351),
  CONSTRAINT enforce_nodata_values_sublimation CHECK (_raster_constraint_nodata_values(sublimation)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_sublimation CHECK (st_numbands(sublimation) = 1),
  CONSTRAINT enforce_out_db_sublimation CHECK (_raster_constraint_out_db(sublimation) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_sublimation CHECK (_raster_constraint_pixel_types(sublimation) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_sublimation CHECK (st_scalex(sublimation)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_sublimation CHECK (st_scaley(sublimation)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10)),
  -- sublimation_blowing constraints
  CONSTRAINT enforce_height_sublimation_blowing CHECK (st_height(sublimation_blowing) = 3351),
  CONSTRAINT enforce_nodata_values_sublimation_blowing CHECK (_raster_constraint_nodata_values(sublimation_blowing)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_sublimation_blowing CHECK (st_numbands(sublimation_blowing) = 1),
  CONSTRAINT enforce_out_db_sublimation_blowing CHECK (_raster_constraint_out_db(sublimation_blowing) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_sublimation_blowing CHECK (_raster_constraint_pixel_types(sublimation_blowing) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_sublimation_blowing CHECK (st_scalex(sublimation_blowing)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_sublimation_blowing CHECK (st_scaley(sublimation_blowing)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10)),
  -- precip_solid constraints
  CONSTRAINT enforce_height_precip_solid CHECK (st_height(precip_solid) = 3351),
  CONSTRAINT enforce_nodata_values_precip_solid CHECK (_raster_constraint_nodata_values(precip_solid)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_precip_solid CHECK (st_numbands(precip_solid) = 1),
  CONSTRAINT enforce_out_db_precip_solid CHECK (_raster_constraint_out_db(precip_solid) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_precip_solid CHECK (_raster_constraint_pixel_types(precip_solid) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_precip_solid CHECK (st_scalex(precip_solid)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_precip_solid CHECK (st_scaley(precip_solid)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10)),
  -- precip_liquid constraints
  CONSTRAINT enforce_height_precip_liquid CHECK (st_height(precip_liquid) = 3351),
  CONSTRAINT enforce_nodata_values_precip_liquid CHECK (_raster_constraint_nodata_values(precip_liquid)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_precip_liquid CHECK (st_numbands(precip_liquid) = 1),
  CONSTRAINT enforce_out_db_precip_liquid CHECK (_raster_constraint_out_db(precip_liquid) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_precip_liquid CHECK (_raster_constraint_pixel_types(precip_liquid) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_precip_liquid CHECK (st_scalex(precip_liquid)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_precip_liquid CHECK (st_scaley(precip_liquid)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10)),
  -- average_temp constraints
  CONSTRAINT enforce_height_average_temp CHECK (st_height(average_temp) = 3351),
  CONSTRAINT enforce_nodata_values_average_temp CHECK (_raster_constraint_nodata_values(average_temp)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_average_temp CHECK (st_numbands(average_temp) = 1),
  CONSTRAINT enforce_out_db_average_temp CHECK (_raster_constraint_out_db(average_temp) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_average_temp CHECK (_raster_constraint_pixel_types(average_temp) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_average_temp CHECK (st_scalex(average_temp)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_average_temp CHECK (st_scaley(average_temp)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
);


CREATE TABLE snodas.tiles (
  "date" date NOT NULL REFERENCES snodas.raster ON DELETE CASCADE,
  "rast" raster,
  "x" integer NOT NULL CHECK (x >= 0),
  "y" integer NOT NULL CHECK (y >= 0),
  "zoom" smallint NOT NULL CHECK (zoom between 0 and 20),
  PRIMARY KEY (date, x, y, zoom),
  CONSTRAINT enforce_height_rast CHECK (st_height(rast) = 256),
  CONSTRAINT enforce_num_bands_rast CHECK (st_numbands(rast) = 1),
  CONSTRAINT enforce_out_db_rast CHECK (_raster_constraint_out_db(rast) = '{f}'::boolean[]),
  CONSTRAINT enforce_srid_rast CHECK (st_srid(rast) = 3857),
  CONSTRAINT enforce_width_rast CHECK (st_width(rast) = 256)
);


CREATE OR REPLACE FUNCTION snodas.reclass_and_warp(
  _r raster
)
RETURNS raster
LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE
AS $$
DECLARE
  stats summarystats;
  lower double precision;
  upper double precision;
BEGIN
  -- do a 2.5 std dev stretch and reproject
  -- the raster to the output crs
  stats := ST_SummaryStats(_r);
  lower := GREATEST(0, stats.mean - 2.5 * stats.stddev);
  upper := LEAST(32767, stats.mean + 2.5 * stats.stddev);
  RETURN (SELECT ST_Transform(ST_Reclass(
    _r,
    1,
    '-32768-0):0, [0-' ||
      lower ||
      '):0, [' ||
      lower ||
      '-' ||
      upper ||
      ']:0-255, (' ||
      upper ||
      '-32767:255'::text,
    '8BUI'::text,
    0::double precision
  ), 3857));
END;
$$;


CREATE OR REPLACE FUNCTION snodas.make_tiles()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
DECLARE
BEGIN
  -- clean out old tiles so we can rebuild
  DELETE FROM snodas.tiles WHERE date = NEW.date;

  -- create the tiles
  INSERT INTO snodas.tiles
    (date, rast, x, y, zoom)
  SELECT
    NEW.date, t.rast, t.x, t.y, t.z
  FROM
    generate_series(0, 7) as zoom,
  LATERAL
    tms_tile_raster_to_zoom(
      snodas.reclass_and_warp(NEW.swe),
      zoom
  ) AS t;

  RETURN NULL;
END;
$$;

CREATE TRIGGER tile_trigger
AFTER INSERT OR UPDATE ON snodas.raster
FOR EACH ROW EXECUTE PROCEDURE snodas.make_tiles();


-- this function will dynamically create a
-- missing tile if we try to load one from
-- a higher zoom level and it is missing
-- we use this function for returning TMS
-- tiles throught the API
CREATE OR REPLACE FUNCTION snodas.tile2png(
  _q_coord tms_tilecoordz,
  _q_date date,
  _q_resample bool DEFAULT true
)
RETURNS bytea
LANGUAGE plpgsql VOLATILE
AS $$
DECLARE
  _q_tile raster;
  _q_rx integer;
  _q_outrast raster;
BEGIN
  -- we try to get the x value and
  -- raster data for the requested tile
  SELECT x, rast
  FROM snodas.raster_tiles
  WHERE
      x = _q_coord.x AND
      y = _q_coord.y AND
      zoom = _q_coord.z AND
      date = _q_date
  INTO _q_rx, _q_tile;

  -- seems kinda weird, but we can tell if we selected a
  -- record or not based on if the tile x is null or not
  -- if the tile x is null then we don't have that tile
  -- so we can resample to create a new one, if requested
  IF _q_rx IS NULL AND _q_resample THEN
    _q_outrast := _q_coord::raster;
    SELECT tms_copy_to_tile(ST_Resample(rast, _q_outrast), _q_outrast)
    FROM snodas.raster_tiles
    WHERE
      date = _q_date AND
      ST_Intersects(rast, _q_outrast)
    ORDER BY zoom DESC
    LIMIT 1
    INTO _q_tile;

    -- if the generated tile has no data then we just set it
    -- to null, reducing the size of the saved row
    IF _q_tile IS NOT NULL AND NOT tms_has_data(_q_tile) THEN
      _q_tile := NULL;
    END IF;

    -- we save the generated tile for next time
    INSERT INTO snodas.raster_tiles (
      rast,
      date,
      x,
      y,
      zoom
    ) VALUES (
      _q_tile,
      _q_date,
      _q_coord.x,
      _q_coord.y,
      _q_coord.z
    );
  END IF;

  -- if the tile is null, either from the initial
  -- query or the resample, then we don't need to
  -- provide a png, as it would be empty anyway
  IF _q_tile IS NULL THEN
    RETURN NULL;
  END IF;

  -- otherwise we return the raster tile as a png
  RETURN (SELECT ST_AsPNG(_q_tile));
END;
$$;


------------------
--  pourpoints
------------------

CREATE TYPE pourpoint.source AS ENUM ('ref', 'awdb', 'user');

CREATE TABLE pourpoint.pourpoint (
  "pourpoint_id" serial PRIMARY KEY,
  "name" text NOT NULL,
  "awdb_id" text,
  "source" pourpoint.source NOT NULL,
  "point" geography(Point, 4326) NOT NULL,
  "polygon" geometry,
  "polygon_simple" geometry,
  "area_meters" float,
  CONSTRAINT polygon_simple_required CHECK (
    CASE
      WHEN polygon is NULL THEN
        polygon_simple is NULL AND
        area_meters is NULL
      WHEN polygon is not NULL THEN
        polygon_simple is not NULL AND
        area_meters is not NULL
    END
  )
);

CREATE TABLE pourpoint.tile (
  "tile" bytea NOT NULL,
  "extent" geometry(POLYGON,3857),
  "x" integer NOT NULL CHECK (x >= 0),
  "y" integer NOT NULL CHECK (y >= 0),
  "zoom" smallint NOT NULL CHECK (zoom between 0 and 24),
  PRIMARY KEY (x, y, zoom)
);


-- this function will dynamically create
-- a tile when we try to load one,
-- if one has not already been cached
CREATE OR REPLACE FUNCTION pourpoint.get_tile(
  _q_x integer,
  _q_y integer,
  _q_z integer
)
RETURNS bytea
LANGUAGE plpgsql VOLATILE
AS $$
DECLARE
  _q_tile bytea;
  _q_tile_ext geometry;
BEGIN
  SELECT
    tile
  FROM
    pourpoint.tile
  WHERE x = _q_x AND y = _q_y AND zoom = _q_z INTO _q_tile;

  IF _q_tile IS NULL THEN
    SELECT (_q_x, _q_y, _q_z)::tms_tilecoordz::geometry INTO _q_tile_ext;
    _q_tile := (SELECT (
      -- this first bit creates the points portion of the tile
      SELECT ST_AsMVT(points, 'points')
      FROM (
        SELECT
          pourpoint_id,
          name,
          source,
          ST_AsMVTGeom(
            geom,
            _q_tile_ext,
            4096,
            100,
            true
          ) AS geom
        FROM (
          SELECT
            id,
            name,
            source,
            ST_Transform(point, 3857) as geom
          FROM pourpoint.pourpoint
          WHERE
            -- limit the points to only those that intersect the tile
            ST_Transform(_q_tile_ext, 4326) && point
        ) as point
      ) AS points) || (
      -- then we append the polygon portion of the tile
      SELECT ST_AsMVT(polygons, 'polygons')
      FROM (
        SELECT
          pourpoint_id,
          name,
          source,
          ST_AsMVTGeom(
            geom,
            _q_tile_ext,
            4096,
            100,
            true
          ) AS geom
          FROM (
            SELECT
              id,
              name,
              source,
              ST_Transform(
                -- we simplify according to the zoom
                -- level to speed processing and to
                -- reduce the size of the generated tile
                ST_SimplifyPreserveTopology(
                  polygon_simple,
                  1000 / (2^_q_z * 4096)
                ),
                3857
              ) as geom
            FROM pourpoint.pourpoint
            WHERE
              -- limit the polygons to only those that intersect the tile
              polygon_simple is not Null AND
              ST_Intersects(ST_Transform(_q_tile_ext, 4326), polygon_simple)
          ) as poly
      ) AS polygons)
    );

    -- we save the generated tile for next time
    INSERT INTO pourpoint.tile (
      tile,
      extent,
      x,
      y,
      zoom
    ) VALUES (
      _q_tile,
      _q_tile_ext,
      _q_x,
      _q_y,
      _q_z
    );
  END IF;

  RETURN _q_tile;
END;
$$;


CREATE OR REPLACE FUNCTION pourpoint.simplify()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  -- simplify then transform (less points for the transform)
  NEW.polygon_simple =
    ST_Transform(ST_SimplifyPreserveTopology(NEW.polygon, .001), 3857);
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION pourpoint.bust_cache()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  -- clean out old tiles when pourpoint data changes
  DELETE FROM pourpoint.tile WHERE (
    ST_Intersects(extent, OLD.polygon_simple) OR
    ST_Intersects(extent, NEW.polygon_simple) OR
    ST_Intersects(extent, OLD.point) OR
    ST_Intersects(extent, NEW.point)
  );
  RETURN NULL;
END;
$$;

-- new pourpoint with polygon and no simplification
CREATE TRIGGER pourpoint_insert_simplify_trigger
BEFORE INSERT ON pourpoint.pourpoint
FOR EACH ROW WHEN (
  NEW.polygon is not NULL AND NEW.polygon_simple is NULL
) EXECUTE PROCEDURE pourpoint.simplify();

CREATE TRIGGER pourpoint_insert_area_trigger
BEFORE INSERT ON pourpoint.pourpoint
FOR EACH ROW WHEN (NEW.polygon is not NULL)
EXECUTE PROCEDURE pourpoint.calc_polygon_area();

-- update on pourpoint with new polygon
-- and no change to simplified polygon
CREATE TRIGGER pourpoint_update_simplify_trigger
BEFORE UPDATE ON pourpoint.pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon AND
  OLD.polygon_simple IS NOT DISTINCT FROM NEW.polygon_simple
) EXECUTE PROCEDURE pourpoint.simplify();

CREATE TRIGGER pourpoint_update_area_trigger
BEFORE UPDATE ON pourpoint.pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon
) EXECUTE PROCEDURE pourpoint.calc_polygon_area();

-- new or deleted pourpoint changes tiles always
CREATE TRIGGER pourpoint_bust_cache_trigger
AFTER INSERT OR DELETE ON pourpoint.pourpoint
FOR EACH ROW EXECUTE PROCEDURE pourpoint.bust_cache();

-- updated pourpoint changes tiles when either
-- the point or simplified polygon are changed
CREATE TRIGGER pourpoint_update_bust_cache_trigger
AFTER UPDATE ON pourpoint.pourpoint
FOR EACH ROW WHEN (
  OLD.point IS DISTINCT FROM NEW.point OR
  OLD.polygon_simple IS DISTINCT FROM NEW.polygon_simple
) EXECUTE PROCEDURE pourpoint.bust_cache();


------------------
--  statistics
------------------

-- need the parameters for snodas rasters
CREATE TABLE snodas.geotransform (
  "rast" raster NOT NULL,
  "valid_dates" daterange NOT NULL PRIMARY KEY,
  EXCLUDE USING gist (valid_dates WITH &&)
);

-- reference geotransforms
INSERT INTO snodas.geotransform (rast, valid_dates) VALUES
  (ST_MakeEmptyRaster(
     6935,
     3351,
     -124.733333333329000,
     52.874999999997797,
     0.008333333333333,
     0.008333333333333,
     0,
     0,
     4326),
   daterange('2013-10-01', NULL, '[)')),
  (ST_MakeEmptyRaster(
     6935,
     3351,
     -124.733749999998366,
     52.874583333332339,
     0.008333333333333,
     0.008333333333333,
     0,
     0,
     4326),
   daterange(NULL, '2013-10-01', '()'));


-- stores raster version of pourpoints with pixel values
-- equal to the pourpoint area in each pixel
-- used for stat calculations
CREATE TABLE pourpoint.rasterized (
  "rasterized_id" serial PRIMARY KEY,
  "pourpoint_id" integer NOT NULL REFERENCES pourpoint.pourpoint ON DELETE CASCADE,
  "valid_dates" daterange NOT NULL REFERENCES snodas.geotransform ON DELETE CASCADE,
  "rast" raster NOT NULL,
  "area_meters" float NOT NULL,
  UNIQUE (pourpoint_id, valid_dates),
  EXCLUDE USING gist (pourpoint_id with =, valid_dates WITH &&)
  -- TODO: add raster constraints like snodas table
);


-- table to store daily pourpoint statistics
-- averaged over area of pourpoint polygon
CREATE TABLE pourpoint.statistics (
  "rasterized_id" integer NOT NULL REFERENCES pourpoint.rasterized ON DELETE CASCADE,
  "pourpoint_id" integer NOT NULL REFERENCES pourpoint.pourpoint ON DELETE CASCADE,
  "date" date NOT NULL REFERENCES snodas.raster ON DELETE CASCADE,
  "snowcover" float NOT NULL               -- percent
    CHECK (snowcover BETWEEN 0 and 100),
  "depth" float NOT NULL                   -- meters
    CHECK (depth >= 0),
  "swe" float NOT NULL                     -- meters
    CHECK (swe >= 0),
  "runoff" float NOT NULL                  -- meters
    --CHECK (runoff >= 0),
  "sublimation" float NOT NULL             -- meters
    --CHECK (sublimation >= 0),
  "sublimation_blowing" float NOT NULL     -- meters
    --CHECK (sublimation_blowing >= 0),
  "precip_solid" float NOT NULL            -- kg/m^2
    --CHECK (precip_solid >= 0),
  "precip_liquid" float NOT NULL           -- kg/m^2
    --CHECK (precip_liquid >= 0),
  "average_temp" float                     -- kelvin (null if nodata in all cells)
    CHECK (average_temp  >= 0),
  PRIMARY KEY (pourpoint_id, date)
);


-- calc stats for a given pourpoint raster
-- and a snodas raster
-- only to be used with pourpoint.rasterize_1
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
      USING HINT = 'Make sure you call pourpoint.calc_stats_1 with a valid pourpoint raster for the SNODAS date.';
  END IF;

  RETURN (
    p.rasterized_id,
    p.pourpoint_id,
    s.date,
    -- percent snowcover:
    -- number of cells with data in both rasters
    -- divided by the total number of cells in the
    -- pourpoint raster multiplied by 100
    ST_Count(ST_MapAlgebra(p.rast, s.swe, '[rast1]', NULL, 'FIRST'))::float / ST_Count(p.rast) * 100,
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
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.sublimation_blowing, '[rast2]/100000', '64BF', 'FIRST', NULL, '0'))).mean,
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
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.average_temp, '[rast2]', '64BF', 'FIRST'))).mean
  );
END;
$$;

-- calc stats for a given pourpoint raster
-- and a snodas raster
-- only to be used with pourpoint.rasterize_2
CREATE OR REPLACE FUNCTION pourpoint.calc_stats_2(
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
      USING HINT = 'Make sure you call pourpoint.calc_stats_2 with a valid pourpoint raster for the SNODAS date.';
  END IF;

  RETURN (SELECT
    p.rasterized_id,
    p.pourpoint_id,
    s.date,
    -- snowcover:
    -- sum the area values where data in both rasters
    -- and divide by the total area
    -- multiplied by 100 to get percent
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.swe, '[rast1]', '64BF', 'FIRST'))).sum / p.area_meters * 100,
    -- depth:
    -- depth in meters times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 1000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.depth, '[rast1] * [rast2]/1000', '64BF', 'FIRST'))).sum / p.area_meters,
    -- swe:
    -- swe in meters times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 1000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.swe, '[rast1] * [rast2]/1000', '64BF', 'FIRST'))).sum / p.area_meters,
    -- runoff:
    -- runoff in meters times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 100000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.runoff, '[rast1] * [rast2]/100000', '64BF', 'FIRST'))).sum / p.area_meters,
    -- sublimation:
    -- sublimation in meters times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 100000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.sublimation, '[rast1] * [rast2]/100000', '64BF', 'FIRST'))).sum / p.area_meters,
    -- sublimation_blowing:
    -- sublimation_blowing in meters times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 100000
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.sublimation_blowing, '[rast1] * [rast2]/100000', '64BF', 'FIRST'))).sum / p.area_meters,
    -- precip_solid:
    -- precip_solid in meters times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 10
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.precip_solid, '[rast1] * [rast2]/10', '64BF', 'FIRST'))).sum / p.area_meters,
    -- precip_liquid:
    -- precip_liquid in meters times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 10
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.precip_liquid, '[rast1] * [rast2]/10', '64BF', 'FIRST'))).sum / p.area_meters,
    -- average_temp:
    -- temperature in kelvin times intersected area of each pixel (weight)
    -- divided by the total pourpoint area to find average
    -- scale factor 1
    (ST_SummaryStats(ST_MapAlgebra(p.rast, s.average_temp, '[rast1] * [rast2]', '64BF', 'FIRST'))).sum / p.area_meters
  );
END;
$$;


-- rasterize a pourpoint to snodas grid
-- this method is less accurate, but much faster
-- stats with this simply consider average of all
-- snodas grid centriods within the pourpoint area
-- with equal weight
CREATE OR REPLACE FUNCTION pourpoint.rasterize_1(
  _q_p pourpoint.pourpoint,
  _q_s snodas.geotransform
)
RETURNS raster
LANGUAGE plpgsql IMMUTABLE
AS $$
BEGIN
  -- the type here is dumb: we should be able to use
  -- 1BUI as this is a boolean mask raster
  -- but ST_MapAlgebra is lame and uses the 0 nodata value
  -- for its output, so we need a datatype that supports -9999
  RETURN (SELECT ST_AsRaster(_q_p.polygon, _q_s.rast, '16BSI'::text, 1, -9999));
END;
$$;

-- rasterize pourpoint to snodas grid
-- this method is "more accurate" (though has
-- loss of precision due to rounding errors)
-- we intersect pourpoint polygon with the
-- snodas pixel geoms and rasterize them
-- with the value of the intersected area
CREATE OR REPLACE FUNCTION pourpoint.rasterize_2(
  _q_p pourpoint.pourpoint,
  _q_s snodas.geotransform
)
RETURNS raster
LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE
AS $$
DECLARE
  _q_r raster;
BEGIN
  WITH spg as (
    SELECT
      (_g).geom as geom,
      (_g).geom::geography as geog
    FROM (
      SELECT
        ST_PixelAsPolygons(
          ST_AsRaster(_q_p.polygon, _q_s.rast, '16BSI'::text, 1, -9999)
        ) as _g
    ) as _h
  )
  SELECT INTO _q_r
    ST_Union(ST_AsRaster(
      spg.geom,
      _q_s.rast,
      '64BF',
      CASE
        WHEN ST_Covers(_q_p.polygon, spg.geom) THEN ST_Area(spg.geog)
        ELSE ST_Area(ST_Intersection(_q_p.polygon::geography, spg.geog))
      END,
      -9999
    )),
    _q_p.area_meters
  FROM spg;
  RETURN _q_r;
END;
$$;

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

-- trigger on insert/update of pourpoint geom
-- to calc all snodas stats
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
      pourpoint.rasterized as p,
      snodas.raster as s,
      pourpoint.calc_stats_1((p), (s)) as r
    WHERE
      NEW.pourpoint_id = p.pourpoint_id AND
      p.valid_dates @> s.date;

  RETURN NULL;
END;
$$;

-- trigger on insert/update of snodas rasters
-- to calc stats for all pourpoint polygons
CREATE OR REPLACE FUNCTION pourpoint.snodas_calc_stats()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  -- in case update try to delete any statistics for date
  DELETE FROM pourpoint.statistics as p
    WHERE p.date = NEW.date;

  -- calc the pourpoint stats for all
  -- pourpoints with this snodas data
  INSERT INTO pourpoint.statistics
    SELECT r.*
    FROM pourpoint.rasterized as p,
      pourpoint.calc_stats_1((p), NEW) as r
    WHERE
      p.valid_dates @> NEW.date;

  RETURN NULL;
END;
$$;

-- new pourpoint with polygon
CREATE TRIGGER pourpoint_insert_rasterize
AFTER INSERT ON pourpoint.pourpoint
FOR EACH ROW WHEN (NEW.polygon is not NULL)
EXECUTE PROCEDURE pourpoint.rasterize();

-- update on pourpoint with new polygon
CREATE TRIGGER pourpoint_update_rasterize
AFTER UPDATE ON pourpoint.pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon
) EXECUTE PROCEDURE pourpoint.rasterize();

-- new pourpoint with polygon
CREATE TRIGGER pourpoint_insert_calc_stats
AFTER INSERT ON pourpoint.pourpoint
FOR EACH ROW WHEN (NEW.polygon is not NULL)
EXECUTE PROCEDURE pourpoint.calc_stats();

-- update on pourpoint with new polygon
CREATE TRIGGER pourpoint_update_calc_stats
AFTER UPDATE ON pourpoint.pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon
) EXECUTE PROCEDURE pourpoint.calc_stats();

-- new or updated snodas
CREATE TRIGGER raster_calc_stats_trigger
AFTER INSERT OR UPDATE ON snodas.raster
FOR EACH ROW EXECUTE PROCEDURE pourpoint.snodas_calc_stats();

-- as such need view on stat table
-- calcs all the things from the base daily stats
