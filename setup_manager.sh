#!/bin/bash

set -e -o pipefail

SCRIPT_DIR=$(dirname $0)

cd $SCRIPT_DIR/management-node

vagrant up
