#!/bin/bash

set -e -o pipefail

apt-get install -y ansible

ansible -i ./production ./field-node/node-base.yml
