#!/bin/bash -eu
# Script to download a specific SNODAS date and import it.
# Call it like this:
#
# ./$0 2018-04-27
#
# Simple.
#
# Date format must be YYYY-MM-DD.


# Need to build a full url like
# ftp://sidads.colorado.edu/pub/DATASETS/NOAA/G02158/masked/2004/02_Feb/SNODAS_20040223.tar
url="ftp://sidads.colorado.edu/pub/DATASETS/NOAA/G02158/masked"


date=$1
year=$(echo ${date} | cut -d - -f 1)
month=$(echo ${date} | cut -d - -f 2)
day=$(echo ${date} | cut -d - -f 3)

case "$month" in
    "01") mo_name="01_Jan" ;;
    "02") mo_name="02_Feb" ;;
    "03") mo_name="03_Mar" ;;
    "04") mo_name="04_Apr" ;;
    "05") mo_name="05_May" ;;
    "06") mo_name="06_Jun" ;;
    "07") mo_name="07_Jul" ;;
    "08") mo_name="08_Aug" ;;
    "09") mo_name="09_Sep" ;;
    "10") mo_name="10_Oct" ;;
    "11") mo_name="11_Nov" ;;
    "12") mo_name="12_Dec" ;;
    *) echo "Date appears invalid: ${date}" >&2 && exit 1 ;;
esac

filename="SNODAS_${year}${month}${day}.tar"
url="${url}/${year}/${mo_name}/${filename}"

curl "${url}"
