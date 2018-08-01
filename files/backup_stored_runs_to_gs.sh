#!/bin/bash

# depends on gsutil from pypi (pip install gsutil)

if [[ "$#" -ne 1 && "$#" -ne 2 ]]; then
    echo "Usage: $(basename $0) gs://bucket/path [/path/containing/runs]"
    exit 1
fi

bucket="$1" # "gs://bucket/path"
if [[ ! -z "$2" && "$2" != " " ]]; then
    CONTAINING_DIR="$2"
else 
  if [ -d "/Volumes/SEQDATA" ]; then
    CONTAINING_DIR="/Volumes/SEQDATA"
  elif [ -d "/media/seqdata" ]; then
    CONTAINING_DIR="/media/seqdata"
  else
    echo "Expected containing directory not found, and no directory provided."
  fi
fi

pushd $CONTAINING_DIR > /dev/null
for dir in $(find . -maxdepth 1 -type d | grep -E "([0-9]{6}_M[0-9]{5}_[0-9]{4}_[0-9]{9}-\w{5}|[0-9]{7,8}_FFSP[0-9]{3,6}_.*)$" | sort)
do
  base=$(basename "$dir")
  if $(gsutil ls "${bucket}${base}.tar.gz" &> /dev/null); then
    echo "${base} already exists; skipping archive creation."
  else
    echo "${base} does not exist; creating archive..."

    # if pigz is available, use it
    if [ -x "$(command -v pigz)" ]; then
      tar cf - "$dir" | pigz > "/tmp/${base}.tar.gz"
    else
      tar -czf "/tmp/${base}.tar.gz" "$dir"
    fi

    gsutil cp "/tmp/${base}.tar.gz" "${bucket}${base}.tar.gz"
    rm "/tmp/${base}.tar.gz"
    #echo "$base"
    #echo "$dir"
  fi
done

echo "Unmatched by flowcell regex:"
find . -maxdepth 1 -type d | grep -vE "([0-9]{6}_M[0-9]{5}_[0-9]{4}_[0-9]{9}-\w{5}|[0-9]{7,8}_FFSP[0-9]{3,6}_.*)$" | sort
popd > /dev/null