#!/bin/bash -eu

function mvp() {
    dir="$2"
    tmp="$2"; tmp="${tmp: -1}"
    [ "${tmp}" != "/" ] && dir="$(dirname "$2")"
    [ -a "${dir}" ] ||
    mkdir -p "${dir}" &&
    mv "$@"
}

function process_raster() {
    local snodas_cmd=$1; shift
    $snodas_cmd loadraster "$1" && mvp "$1" "$2" && echo "Processed $1" || echo "Error processing $1"
}

export -f process_raster
export -f mvp

workers=$1
src_dir=${2%/}
out_dir=${3%/}
snodas_cmd=$4

pushd "${src_dir}" > /dev/null

# we get SNODAS files pushed to us in a weird format
# to accommodate, we find all .grz files (if any)
# and build into the equally-strange SNODAS tar format
dates=$(ls *.grz 2>/dev/null | grep -oP '(?<!\d)\d{8}' | sort -u)
for date in ${dates[@]}; do
    (
        tmp=$(mktemp -d)
	trap "rm -r $tmp" EXIT

        year=${date:0:4}
        month=${date:4:2}
        day=${date:6:2}

        # we get the files as tar.gz in a weird .grz ext
        # we need each gzipped individually in a tar, stupidly
        # so for each .grz we untar/expand it to tmp
        for f in *$date*.grz; do
            fname="${f%.*}"
            tar -xzf $f -C $tmp
        done

        # now we gzip each file in the tmp dir
        (cd $tmp; ls | xargs -n 1 gzip)

        # lastly we tar up all the files in the tmp dir
        # outputting to the current dir
        file=SNODAS_${year}${month}${day}.tar
        tar -cf $file -C $tmp .

	# and we can remove the original grz files
	rm *$date*.grz
    )
done

popd > /dev/null

# now we find all the tar files in the src dir
tars=$(find "${src_dir}" -name "*.tar")

# we can process the tars now
(for file in ${tars[@]}; do
    in="${file}"
    filename=$(basename $file)
    date=$(echo $filename | grep -oP '(?<!\d)\d{8}')
    year=${date:0:4}
    month=${date:4:2}
    out="${out_dir}/${year}/${month}/${filename}"
    [ -f "${in}" ] || continue
    echo "${in} ${out}"
done) | xargs -r -L1 -P ${workers} -t bash -c 'process_raster "$1" "$2" "3"' -- ${snodas_cmd}
