#!/bin/bash

# depends on gsutil from pypi (pip install gsutil)

bucket="gs://sequencing/flowcells/miseq/"

cd /media/seqdata
for dir in $(find . -maxdepth 1 -type d | grep "[0-9]\{6\}_M[0-9]\{5\}_[0-9]\{4\}_[0-9]\{9\}-\w\{5\}$" | sort)
do
  base=$(basename "$dir")
  if $(gsutil ls "${bucket}${base}.tar.gz" &> /dev/null); then
    echo "${base} already exists; skipping archive creation."
  else
    echo "${base} does not exist; creating archive..."
    tar -czf "${base}.tar.gz" "$dir"
    gsutil cp "${base}.tar.gz" "${bucket}${base}.tar.gz"
    rm "${base}.tar.gz"
    #echo "$base"
    #echo "$dir"
  fi
done