#!/bin/bash

MAX_PROCS=10
URL='https://www.nrcs.usda.gov/Internet/WCIS/sitedata/MONTHLY/SRVO/'

curl ${URL} -s | grep -o 'href=".*\.json"' | cut -d '"' -f 2 | xargs -P ${MAX_PROCS} -I {} bash -c "curl -s ${URL}{} | snodas loadstreamflow -"
