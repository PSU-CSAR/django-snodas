#!/bin/bash


function mvp() {
    dir="$2"
    tmp="$2"; tmp="${tmp: -1}"
    [ "${tmp}" != "/" ] && dir="$(dirname "$2")"
    [ -a "${dir}" ] ||
    mkdir -p "${dir}" &&
    mv "$@"
}


function process_raster() {
    snodas loadraster "$1" && mvp "$1" "$2" && echo "Processed $1" || echo "Error processing $1"
}

export -f process_raster
export -f mvp


workers=$1
src_dir=$2
out_dir=$3


# get all files to process
shopt -s globstar
pushd "${src_dir}" > /dev/null
files=( ** )
popd > /dev/null

(for file in ${files[@]}; do
    in="${src_dir}/${file}"
    out="${out_dir}/${file}"
    [ -f "${in}" ] || continue
    echo "${in} ${out}"
done) | xargs -r -L1 -P ${workers} -t bash -c 'process_raster "$0" "$1"'
