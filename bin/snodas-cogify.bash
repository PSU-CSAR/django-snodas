#!/usr/bin/env bash
# To speed up a single/serialzed execution(s), one can use parallelism via
# export GDAL_NUM_THREADS=ALL_CPUS

set -euo pipefail

find_this () {
    THIS="${1:?'must provide script path, like "${BASH_SOURCE[0]}" or "$0"'}"
    trap "echo >&2 'FATAL: could not resolve parent directory of ${THIS}'" EXIT
    [ "${THIS:0:1}"  == "/" ] || THIS="$(pwd -P)/${THIS}"
    THIS_DIR="$(dirname -- "${THIS}")"
    THIS_DIR="$(cd -P -- "${THIS_DIR}" && pwd)"
    THIS="${THIS_DIR}/$(basename -- "${THIS}")"
    trap "" EXIT
}


find_this "${BASH_SOURCE[0]}"

. "${THIS_DIR}/lib.d/lib.bash"

outdir="${1:?"$(pwd)"}"

[ -d "${outdir}" ] && [ -d "${outdir}" ] || {
    ercho "Output dir does not exist or is not writable: '${outdir}'" 1
}

tmpdir="$(mktemp -d)"
trap "rm -rf ${tmpdir}" EXIT

tar -xf - -C "${tmpdir}"

swe_dat="$(basename "${tmpdir}/"????????${SNODAS_PRODUCT_TYPE_SWE}*.dat.gz)"
date="${swe_dat:27:8}"

outdir="${outdir}/${date}"
mkdir -p "${outdir}"

for dat_gz in "${tmpdir}/"*.dat.gz; do
    hdr_gz="$(echo "${dat_gz%.dat.gz}".[Ht][dx][rt].gz)"
    dat="${dat_gz%.gz}"
    hdr="${hdr_gz%.gz}"
    cog="${outdir}/$(basename "${dat%.dat}.tif")"

    gunzip <"${dat_gz}" >"${dat}"
    gunzip <"${hdr_gz}" >"${hdr}"

    (
        set -x
        gdal_translate -of cog "${hdr}" "${cog}" \
            -stats \
            -co BLOCKSIZE=256 \
            -co RESAMPLING=AVERAGE \
            -co PREDICTOR=2 \
            -co COMPRESS=DEFLATE \
            -co LEVEL=12
    )
done
