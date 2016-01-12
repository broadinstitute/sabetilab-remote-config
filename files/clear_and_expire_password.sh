#!/bin/bash

set -e -o pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $(basename $0) username"
    exit 1
fi

passwd --status $1 | awk -F ' ' '{print $2}' | grep 'P' &> /dev/null || passwd -d -e $1
