CREATE EXTENSION pg_tms CASCADE;


---------------
--  generic
---------------

CREATE OR REPLACE FUNCTION calc_polygon_area()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  NEW.area_meters = ST_Area(NEW.polygon);
  RETURN NEW;
END;
$$;


---------------
--  SNODAS
---------------

CREATE TABLE "snodas" (
  "snodas_id" serial PRIMARY KEY,
  "swe" raster NOT NULL,
  "depth" raster NOT NULL,
  "runoff" raster NOT NULL,
  "sublimation" raster NOT NULL,
  "sublimation_blowing" raster NOT NULL,
  "precip_solid" raster NOT NULL,
  "precip_liquid" raster NOT NULL,
  "average_temp" raster NOT NULL,
  "date" date NOT NULL,
  -- swe constraints
  CONSTRAINT enforce_height_swe CHECK (st_height(swe) = 3351),
  CONSTRAINT enforce_nodata_values_swe CHECK (_raster_constraint_nodata_values(swe)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_swe CHECK (st_numbands(swe) = 1),
  CONSTRAINT enforce_out_db_swe CHECK (_raster_constraint_out_db(swe) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_swe CHECK (_raster_constraint_pixel_types(swe) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_swe CHECK (st_scalex(swe)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_swe CHECK (st_scaley(swe)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
  -- depth constraints
  CONSTRAINT enforce_height_depth CHECK (st_height(depth) = 3351),
  CONSTRAINT enforce_nodata_values_depth CHECK (_raster_constraint_nodata_values(depth)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_depth CHECK (st_numbands(depth) = 1),
  CONSTRAINT enforce_out_db_depth CHECK (_raster_constraint_out_db(depth) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_depth CHECK (_raster_constraint_pixel_types(depth) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_depth CHECK (st_scalex(depth)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_depth CHECK (st_scaley(depth)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
  -- runoff constraints
  CONSTRAINT enforce_height_runoff CHECK (st_height(runoff) = 3351),
  CONSTRAINT enforce_nodata_values_runoff CHECK (_raster_constraint_nodata_values(runoff)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_runoff CHECK (st_numbands(runoff) = 1),
  CONSTRAINT enforce_out_db_runoff CHECK (_raster_constraint_out_db(runoff) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_runoff CHECK (_raster_constraint_pixel_types(runoff) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_runoff CHECK (st_scalex(runoff)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_runoff CHECK (st_scaley(runoff)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
  -- sublimation constraints
  CONSTRAINT enforce_height_sublimation CHECK (st_height(sublimation) = 3351),
  CONSTRAINT enforce_nodata_values_sublimation CHECK (_raster_constraint_nodata_values(sublimation)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_sublimation CHECK (st_numbands(sublimation) = 1),
  CONSTRAINT enforce_out_db_sublimation CHECK (_raster_constraint_out_db(sublimation) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_sublimation CHECK (_raster_constraint_pixel_types(sublimation) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_sublimation CHECK (st_scalex(sublimation)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_sublimation CHECK (st_scaley(sublimation)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
  -- sublimation_blowing constraints
  CONSTRAINT enforce_height_sublimation_blowing CHECK (st_height(sublimation_blowing) = 3351),
  CONSTRAINT enforce_nodata_values_sublimation_blowing CHECK (_raster_constraint_nodata_values(sublimation_blowing)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_sublimation_blowing CHECK (st_numbands(sublimation_blowing) = 1),
  CONSTRAINT enforce_out_db_sublimation_blowing CHECK (_raster_constraint_out_db(sublimation_blowing) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_sublimation_blowing CHECK (_raster_constraint_pixel_types(sublimation_blowing) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_sublimation_blowing CHECK (st_scalex(sublimation_blowing)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_sublimation_blowing CHECK (st_scaley(sublimation_blowing)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
  -- precip_solid constraints
  CONSTRAINT enforce_height_precip_solid CHECK (st_height(precip_solid) = 3351),
  CONSTRAINT enforce_nodata_values_precip_solid CHECK (_raster_constraint_nodata_values(precip_solid)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_precip_solid CHECK (st_numbands(precip_solid) = 1),
  CONSTRAINT enforce_out_db_precip_solid CHECK (_raster_constraint_out_db(precip_solid) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_precip_solid CHECK (_raster_constraint_pixel_types(precip_solid) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_precip_solid CHECK (st_scalex(precip_solid)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_precip_solid CHECK (st_scaley(precip_solid)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
  -- precip_liquid constraints
  CONSTRAINT enforce_height_precip_liquid CHECK (st_height(precip_liquid) = 3351),
  CONSTRAINT enforce_nodata_values_precip_liquid CHECK (_raster_constraint_nodata_values(precip_liquid)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_precip_liquid CHECK (st_numbands(precip_liquid) = 1),
  CONSTRAINT enforce_out_db_precip_liquid CHECK (_raster_constraint_out_db(precip_liquid) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_precip_liquid CHECK (_raster_constraint_pixel_types(precip_liquid) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_precip_liquid CHECK (st_scalex(precip_liquid)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_precip_liquid CHECK (st_scaley(precip_liquid)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
  -- average_temp constraints
  CONSTRAINT enforce_height_average_temp CHECK (st_height(average_temp) = 3351),
  CONSTRAINT enforce_nodata_values_average_temp CHECK (_raster_constraint_nodata_values(average_temp)::numeric(16,10)[] = '{-9999}'::numeric(16,10)[]),
  CONSTRAINT enforce_num_bands_average_temp CHECK (st_numbands(average_temp) = 1),
  CONSTRAINT enforce_out_db_average_temp CHECK (_raster_constraint_out_db(average_temp) = '{f}'::boolean[]),
  CONSTRAINT enforce_pixel_types_average_temp CHECK (_raster_constraint_pixel_types(average_temp) = '{16BSI}'::text[]),
  CONSTRAINT enforce_scalex_average_temp CHECK (st_scalex(average_temp)::numeric(25,10) = 0.00833333333333328::numeric(25,10)),
  CONSTRAINT enforce_scaley_average_temp CHECK (st_scaley(average_temp)::numeric(25,10) = (-0.00833333333333333)::numeric(25,10))
);


CREATE TABLE "snodas_swe_tiles" (
  "tile_id" serial PRIMARY KEY,
  "parent" integer NOT NULL REFERENCES "snodas" ON DELETE CASCADE,
  "rast" raster,
  "x" integer NOT NULL CHECK (x >= 0),
  "y" integer NOT NULL CHECK (y >= 0),
  "zoom" smallint NOT NULL CHECK (zoom between 0 and 20)
  CONSTRAINT enforce_height_rast CHECK (st_height(rast) = 256),
  CONSTRAINT enforce_num_bands_rast CHECK (st_numbands(rast) = 1),
  CONSTRAINT enforce_out_db_rast CHECK (_raster_constraint_out_db(rast) = '{f}'::boolean[]),
  CONSTRAINT enforce_srid_rast CHECK (st_srid(rast) = 3857),
  CONSTRAINT enforce_width_rast CHECK (st_width(rast) = 256)
);


CREATE OR REPLACE FUNCTION tile_snodas()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
DECLARE
  warped raster;
  stats summarystats;
  lower double precision;
  upper double precision;
BEGIN
  -- clean out old tiles so we can rebuild
  DELETE FROM snodas_swe_tiles WHERE parent = NEW.rid;
  
  -- do a 2.5 std dev stretch on the imagery
  stats := ST_SummaryStats(NEW.swe);
  lower := GREATEST(0, stats.mean - 2.5 * stats.stddev);
  upper := LEAST(32767, stats.mean + 2.5 * stats.stddev);
  warped := ST_Reclass(
    NEW.swe,
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
  );
  
  -- reproject the raster to the output crs
  warped := ST_Transform(warped, 3857);
      
  -- generate the tiles inserting each into the tile table
  -- we override the defaults and generate zoom levels 0 through 7
  INSERT INTO snodas_swe_tiles
    (parent, rast, x, y, zoom)
  SELECT
    NEW.snodas_id, t.rast, t.x, t.y, t.z
  FROM tms_build_tiles(warped, 0, 7) AS t;
  RETURN NULL;
END;
$$;

CREATE TRIGGER snodas_tile_trigger
AFTER INSERT OR UPDATE ON snodas
FOR EACH ROW EXECUTE PROCEDURE tile_snodas();


-- this function will dynamically create a
-- missing tile if we try to load one from
-- a higher zoom level and it is missing
-- we use this function for returning TMS
-- tiles throught the API
CREATE OR REPLACE FUNCTION snodas2png(
  _q_coord tms_tilecoordz,
  _q_rdate date,
  _q_resample bool DEFAULT true
)
RETURNS bytea
LANGUAGE plpgsql VOLATILE
AS $$
DECLARE
  _q_tile raster;
  _q_rid integer;
  _q_parent_id integer;
  _q_outrast raster;
BEGIN
  -- find the parent raster so we can query just its tiles
  SELECT snodas_id FROM snodas WHERE date = _q_rdate INTO _q_parent_id;

  -- we try to get the tile rid and
  -- raster data for the request tile
  SELECT tile_id, rast
  FROM snodas_swe_tiles
  WHERE
      x = _q_coord.x AND
      y = _q_coord.y AND
      zoom = _q_coord.z AND
      parent = _q_parent_id
  INTO _q_rid, _q_tile;

  -- if the tile rid is null then we don't have that tile
  -- so we can resample to create a new one, if requested
  IF _q_rid IS NULL AND _q_resample THEN
    _q_outrast := _q_coord::raster;
    SELECT tms_copy_to_tile(ST_Resample(rast, _q_outrast), _q_outrast)
    FROM snodas_swe_tiles
    WHERE
      parent = _q_parent_id AND
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
    INSERT INTO snodas_swe_tiles (
      rast,
      parent,
      x,
      y,
      zoom
    ) VALUES (
      _q_tile,
      _q_parent_id,
      _q_coord.x,
      _q_coord.y,
      _q_coord.z
    );
  END IF;

  -- if the tile is null, either from the inital
  -- query or the resample, then we don't need to
  -- provide a png, as it would just be empty
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

CREATE TYPE pourpoint_source AS ENUM ('ref', 'awdb', 'user');

CREATE TABLE "pourpoint" (
  "pouroint_id" serial PRIMARY KEY,
  "name" text NOT NULL,
  "awdb_id" text,
  "source" pourpoint_source NOT NULL,
  "point" geography(Point, 4326) NOT NULL,
  "polygon" geography(MultiPolygon, 4326),
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


CREATE TABLE "pourpoint_tiles" (
  "tile_id" serial PRIMARY KEY,
  "tile" bytea NOT NULL,
  "extent" geometry(POLYGON,3857),
  "x" integer NOT NULL CHECK (x >= 0),
  "y" integer NOT NULL CHECK (y >= 0),
  "zoom" smallint NOT NULL CHECK (zoom between 0 and 24)
);


-- this function will dynamically create
-- a tile when we try to load one,
-- if one has not already been cached
CREATE OR REPLACE FUNCTION get_pourpoint_tile(
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
   pourpoint_tiles
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
            st_transform(point, 3857) as geom
          FROM pourpoint
          WHERE
            -- limit the points to only those that intersect the tile
            st_transform(_q_tile_ext, 4326) && point
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
              st_transform(
                -- we simplify according to the zoom
                -- level to speed processing and to
                -- reduce the size of the generated tile
                st_simplifypreservetopology(
                  polygon_simple,
                  1000 / (2^_q_z * 4096)
                ),
                3857
              ) as geom
            FROM pourpoint
            WHERE
              -- limit the polygons to only those that intersect the tile
              st_transform(_q_tile_ext, 4326) && polygon_simple AND
              polygon_simple is not Null
          ) as poly
      ) AS polygons)
    );
      
    -- we save the generated tile for next time
    INSERT INTO pourpoint_tiles (
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


CREATE OR REPLACE FUNCTION pourpoint_simplify()
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

CREATE OR REPLACE FUNCTION pourpoint_bust_cache()
RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  -- clean out old tiles when pourpoint data changes
  DELETE FROM pourpoint_tile WHERE (
    extent && OLD.polygon_simple OR
    extent && NEW.polygon_simple OR
    extent && OLD.point OR
    extent && NEW.point
  );
  RETURN NULL;
END;
$$;

-- new pourpoint with polygon and no simplification
CREATE TRIGGER pourpoint_insert_simplify_trigger
BEFORE INSERT ON pourpoint
FOR EACH ROW
WHEN (NEW.polygon is not NULL AND NEW.polygon_simple is NULL)
EXECUTE PROCEDURE pourpoint_simplify();

CREATE TRIGGER pourpoint_insert_area_trigger
BEFORE INSERT ON pourpoint
FOR EACH ROW
WHEN (NEW.polygon is not NULL)
EXECUTE PROCEDURE calc_polygon_area();

-- update on pourpoint with new polygon
-- and no change to simplified polygon
CREATE TRIGGER pourpoint_update_simplify_trigger
BEFORE UPDATE ON pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon AND
  OLD.polygon_simple IS NOT DISTINCT FROM NEW.polygon_simple
) EXECUTE PROCEDURE pourpoint_simplify();

CREATE TRIGGER pourpoint_update_area_trigger
BEFORE UPDATE ON pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon
) EXECUTE PROCEDURE calc_polygon_area();

-- new or deleted pourpoint changes tiles always
CREATE TRIGGER pourpoint_bust_cache_trigger
AFTER INSERT OR DELETE ON pourpoint
FOR EACH ROW EXECUTE PROCEDURE pourpoint_bust_cache();

-- updated pourpoint changes tiles when either
-- the point or simplified polygon are changed
CREATE TRIGGER pourpoint_update_bust_cache_trigger
AFTER UPDATE ON pourpoint
FOR EACH ROW WHEN (
  OLD.point IS DISTINCT FROM NEW.point OR
  OLD.polygon_simple IS DISTINCT FROM NEW.polygon_simple
) EXECUTE PROCEDURE pourpoint_bust_cache();


------------------
--  statistics
------------------

-- need the parameters for snodas rasters
CREATE TABLE "snodas_geotransform" (
  "geotransform_id" serial PRIMARY KEY,
  "rast" raster NOT NULL,
  "valid_dates" daterange NOT NULL
  -- TODO: constraints on date range no overlaps and is continuous
)

-- reference geotransforms
INSERT INTO snodas_geotransform VALUES
  (ST_MakeEmptyRaster(
     6935,
     3351,
     -124.733333333329000,
     52.874999999997797
     0.008333333333333,
     -0.008333333333333
     0,
     0,
     4326,
   daterange('2013-10-01', NULL, '[)')),
  (ST_MakeEmptyRaster(
     6935,
     3351,
     -124.733749999998366,
     52.874583333332339
     0.008333333333333,
     -0.008333333333333
     0,
     0,
     4326,
   daterange(NULL, '2013-10-01', '()'));
  

-- snodas pixel area table used to calc statistics
CREATE TABLE "snodas_pixel_geom" (
  "row" integer NOT NULL,
  "col" integer NOT NULL,
  "polygon" geography(Polygon, 4326) NOT NULL,
  "date_range" daterange NOT NULL,
  "area_meters" float NOT NULL
  PRIMARY_KEY(row, col)
)

CREATE TRIGGER snodas_pixel_area_trigger
BEFORE INSERT OR UPDATE ON snodas_pixel_geom
FOR EACH ROW EXECUTE PROCEDURE calc_polygon_area();

-- generate all pixel geometries from the
-- masked snodas raster grid geotransform
-- this is the current grid
INSERT INTO snodas_pixel_geom
  SELECT
    (_g).x,
    (_g).y,
    (_g).geom,
    date_range
  FROM (
    SELECT
      date_range,
      ST_PixelAsPolygons(
        ST_AddBand(
          rast,
        '8BUI')
      ) as _g
    FROM snodas_geotransform
  ) as _h;


-- join table between the pixel area table and the pour point table
-- used in stat calculations
CREATE TYPE "snodas_pourpoint_pixel_join" (
  "pourpoint_id" integer NOT NULL REFERENCES "pourpoint" ON DELETE CASCADE,
  "polygon" geography(Polygon, 4326) NOT NULL,
  "intersection_area" float NOT NULL,
)


-- join table between the pixel area table and the pour point table
-- used in stat calculations
CREATE TABLE "pourpoint_rasterized" (
  "pourpoint_id" integer NOT NULL REFERENCES "pourpoint" ON DELETE CASCADE,
  "valid_dates" daterange NOT NULL,
  "rast" raster NOT NULL,
  "area_meters" float NOT NULL,
  PRIMARY KEY (pourpoint_id, valid_dates)
  -- TODO: add raster constraints like snodas table
)


-- table to store daily pourpoint statistics
-- averaged over area of pourpoint polygon
CREATE TABLE "pourpoint_snodas_statistics" (
  "pourpoint_id" integer NOT NULL REFERENCES "pourpoint" ON DELETE CASCADE,
  "date" date NOT NULL,
  "percent_snowcover" float NOT NULL,
  "depth" float NOT NULL,                -- meters
  "swe" float NOT NULL,                  -- meters
  "runoff" float NOT NULL,               -- meters
  "submlimation" float NOT NULL,         -- meters
  "sublimation_blowing" float NOT NULL,  -- meters
  "precip_solid" float NOT NULL,         -- kg/m^2
  "precip_liquid" float NOT NULL,        -- kg/m^2
  "temperature" float NOT NULL,          -- kelvin
  PRIMARY KEY (pourpoint_id, date)
)


-- calc stats for a given set of pourpoint pixel
-- geom records and a set of snodas records
CREATE OR UPDATE FUNCTION pourpoint_calc_stats(
  _q_prast pourpoint_rasterized,
  _q_snodas snodas,
)
RETURNS NULL
LANGUAGE plpgsql VOLATILE
AS $$
BEGIN
  INSERT INTO pourpoint_snodas_statistics
    SELECT
      p.pourpoint_id,
      s.date,
      -- percent_snowcover:
      -- sum the area values where data in both rasters
      -- and divide by the total area * 100
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.swe, 'rast2.val', '64BF', 'FIRST')).sum / p.area_meters * 100,
      -- depth:
      -- depth in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 1000
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.depth, 'rast1.val * raster2.val/1000', '64BF', 'FIRST')).sum / p.area_meters,
      -- swe:
      -- swe in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 1000
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.swe, 'rast1.val * raster2.val/1000', '64BF', 'FIRST')).sum / p.area_meters,
      -- runoff:
      -- runoff in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 100000
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.runoff, 'rast1.val * raster2.val/100000', '64BF', 'FIRST')).sum / p.area_meters,
      -- sublimation:
      -- sublimation in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 100000
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.sublimation, 'rast1.val * raster2.val/100000', '64BF', 'FIRST')).sum / p.area_meters,
      -- sublimation_blowing:
      -- sublimation_blowing in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 100000
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.sublimation_blowing, 'rast1.val * raster2.val/100000', '64BF', 'FIRST')).sum / p.area_meters,
      -- precip_solid:
      -- precip_solid in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 10
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.precip_solid, 'rast1.val * raster2.val/10', '64BF', 'FIRST')).sum / p.area_meters,
      -- precip_liquid:
      -- precip_liquid in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 10
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.precip_liquid, 'rast1.val * raster2.val/10', '64BF', 'FIRST')).sum / p.area_meters,
      -- temperature:
      -- temperature in meters times intersected area of each pixel (weight)
      -- divided by the total pourpoint area to find average
      -- scale factor 1
      (ST_SummaryStats(ST_MapAlgebra(p.rast, s.temperature, 'rast1.val * raster2.val', '64BF', 'FIRST')).sum / p.area_meters,
    FROM _q_prast as p, _q_snodas as s
    WHERE p.date_range @> s.date;
  RETURN NULL;
END;
$$;

-- trigger on insert/update of pourpoint geom
-- to make pixel join table entries with areas
CREATE OR UPDATE FUNCTION pourpoint_rasterize_and_calc()
RETURNS TRIGGER
LANGUAGED plpgsql VOLATILE
AS $$
BEGIN
  -- if update delete existing rasterization
  DELETE FROM pourpoint_rasterized
    WHERE pourpoint_id = NEW.pourpoint_id;
  -- and also any statistics
  DELETE FROM pourpoint_snodas_statistics
    WHERE pourpoint_id = NEW.pourpoint_id;

  -- create a new rasterization
  -- we intersect pourpoint polygon with the
  -- snodas pixel geoms and rasterize them
  -- with the value of the intersected area
  INSERT INTO pourpoint_rasterized
    SELECT
      NEW.pourpoint_id,
      spg.date_range,
      ST_Union(ST_AsRaster(
        spg.polygon,
        (SELECT rast FROM snodas_geotransform where date_range == spg.date_range),
        '64BF',
        CASE
          WHEN ST_Contains(NEW.polygon, spg.polygon) THEN spg.area_meters
          ELSE ST_Area(ST_Intersection(NEW.polygon, spg.polygon))
        END,
        -9999
      ),
      NEW.area_meters
    FROM
      snodas_pixel_geom as spg
    WHERE
      NEW.polygon && spg.polygon
    GROUP BY
      spg.date_range;

  -- calc the pourpoint stats for all
  -- snodas dates
  SELECT pourpoint_calc_stats(
    -- grab the pourpoint raster rows
    (SELECT * FROM pourpoint_rasterized as _p
      WHERE NEW.pourpoint_id = p.pourpoint_id) as p,
    (SELECT * FROM snodas) as s
  );
  
  RETURN NULL;
END;
$$;

-- trigger on insert/update of snodas rasters
-- to calc stats for all pourpoint polygons
CREATE OR UPDATE FUNCTION snodas_pourpoint_calc_stats()
RETURNS TRIGGER
LANGUAGED plpgsql VOLATILE
AS $$
BEGIN
  -- in case update try to delete any statistics for date
  DELETE FROM pourpoint_snodas_statistics as p
    WHERE p.date = NEW.date;

  -- calc the pourpoint stats for all
  -- pourpoints with this snodas data
  SELECT pourpoint_calc_stats(
    -- grab the pourpoint raster rows
    (SELECT * FROM pourpoint_rasterized) as p,
    NEW
  );
  
  RETURN NULL;
END;
$$;

-- new pourpoint with polygon
CREATE TRIGGER pourpoint_insert_rasterize_and_calc
AFTER INSERT ON pourpoint
FOR EACH ROW
WHEN (NEW.polygon is not NULL)
EXECUTE PROCEDURE pourpoint_rasterize_and_calc();

-- update on pourpoint with new polygon
CREATE TRIGGER pourpoint_update_rasterize_and_calc
AFTER UPDATE ON pourpoint
FOR EACH ROW WHEN (
  OLD.polygon IS DISTINCT FROM NEW.polygon
) EXECUTE PROCEDURE pourpoint_rasterize_and_calc();

-- new or updated snodas
CREATE TRIGGER snodas_pourpoint_calc_stats_trigger
AFTER INSERT OR UPDATE ON snodas
FOR EACH ROW
EXECUTE PROCEDURE snodas_pourpoint_calc_stats();

-- as such need view on stat table
-- calcs all the things from the base daily stats
