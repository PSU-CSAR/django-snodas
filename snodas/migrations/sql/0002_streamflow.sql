-- this file should be run as the 'app' user
-- so the 'app' user becomes the owner of all

--------------
-- schemas
--------------
CREATE SCHEMA streamflow;


------------------
--  streamflow
------------------

CREATE TABLE streamflow.monthly (
  "awdb_id" text NOT NULL,
  "month" date NOT NULL,
  "acrefeet" float,
  PRIMARY KEY (awdb_id, month)
);
