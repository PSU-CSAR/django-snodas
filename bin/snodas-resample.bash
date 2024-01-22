#!/usr/bin/env bash

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


snodas_resample () {
    local GRID INPUT OUTPUT USAGE
    local XMIN XMAX YMIN YMAX
    USAGE=$(cat <<EOF
USAGE: $0 ${FUNCNAME[0]} [ OPTIONS ] INPUT OUTPUT

Resample a raster dataset to the SNODAS grid, outputting a COG.

OPTIONS:
    -h/--help           show this message
    -g/--grid old|new   specify which SNODAS grid to resmaple to
EOF
)

    . $GETOPT -n "$0: ${FUNCNAME[0]}" -o "hg:" -l "help,grid:" -- "$@"

    local ARG i=0
    while [ "$i" -lt "${#OPTS[@]}" ]; do
        ARG="${OPTS[$i]}"
        i=$((i+1))
        case $ARG in
            -h|--help)
                echou "$USAGE"
                ;;
            -g|--grid)
                GRID="${OPTS[$i]}"
                i=$((i+1))
                ;;
            --)
                break
                ;;
            *)
                ercho "${FUNCNAME[0]}: unknown option: '$ARG'" 1
                ;;
        esac
    done

    INPUT="${ARGS[0]:?"${FUNCNAME[0]}: must provide path to input DEM dataset"}"
    OUTPUT="${ARGS[1]:?"${FUNCNAME[0]}: must provide desired output file path"}"

    if [ -z "${GRID:-}" ]; then
        ercho "${FUNCNAME[0]}: must provide a value for the resampling grid" 1
    elif [ "${GRID}" = "new" ]; then
        XMIN=${SNODAS_NEW_GRID_XMIN}
        XMAX=${SNODAS_NEW_GRID_XMAX}
        YMIN=${SNODAS_NEW_GRID_YMIN}
        YMAX=${SNODAS_NEW_GRID_YMAX}
    elif [ "${GRID}" = "old" ]; then
        XMIN=${SNODAS_OLD_GRID_XMIN}
        XMAX=${SNODAS_OLD_GRID_XMAX}
        YMIN=${SNODAS_OLD_GRID_YMIN}
        YMAX=${SNODAS_OLD_GRID_YMAX}
    else
        ercho "${FUNCNAME[0]}: unknown grid '${GRID}'. Valid values: 'new', 'old'." 1
    fi

    export GDAL_NUM_THREADS=ALL_CPUS
    set -x
    gdalwarp \
        -overwrite \
        -r average \
        -te ${XMIN} ${YMIN} ${XMAX} ${YMAX} \
        -ts ${SNODAS_COLS} ${SNODAS_ROWS} \
        -te_srs EPSG:4326 \
        -t_srs EPSG:4326 \
        -multi \
        -of COG \
        -co BLOCKSIZE=256 \
        -co PREDICTOR=2 \
        -co RESAMPLING=AVERAGE \
        -co COMPRESS=DEFLATE \
        -co LEVEL=12 \
        "${INPUT}" \
        "${OUTPUT}"
}

snodas_resample "$@"
