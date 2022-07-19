#!/bin/bash -eux

output_dir="${1:?must specify the pourpoint output dir}"
output_dir="$(realpath -e "$output_dir")"

[ -d "$output_dir" -a -r "$output_dir" ] || {
  echo >&2 "output is not a directory or is not writable"
  exit 1
}

if command -v cygpath > /dev/null; then
  tmpdir="$(mktemp -d -p /c/Temp/)"
  winpath="$(cygpath -w "${tmpdir}")"
else
  tmpdir="$(mktemp -d)"
fi
trap "rm -r '${tmpdir}'" EXIT

SNODAS_DATABASE_USER=postgres snodas dbshell <<EOF
do \$\$
  declare
    feature record;
    file varchar;
  begin
    for feature in
    select awdb_id, replace(awdb_id, ':', '_') _awdb_id from pourpoint.pourpoint
    loop
      file := '${winpath:-tmpdir}/'||feature._awdb_id||'.geojson';
      execute format('copy (
        select case when polygon is null then
          json_build_object(
            ''type'', ''Feature'',
            ''id'', feature.awdb_id,
            ''geometry'', ST_AsGeoJSON(feature.point)::json,
            ''properties'', json_build_object(
              ''name'', feature.name,
              ''source'', feature.source
            )
          )
        else
          json_build_object(
            ''type'', ''GeometryCollection'',
            ''id'', feature.awdb_id,
            ''geometries'',  json_build_array(
              ST_AsGeoJSON(feature.point)::json,
              ST_AsGeoJSON(ST_Transform(feature.polygon, 4326))::json
            ),
            ''properties'', json_build_object(
              ''name'', feature.name,
              ''source'', feature.source
            )
          )
        end
        from pourpoint.pourpoint feature where feature.awdb_id = %L
      ) TO %L', feature.awdb_id, file);
    end loop;
  end;
\$\$;
EOF

cp "${tmpdir}"/* "${output_dir}"
