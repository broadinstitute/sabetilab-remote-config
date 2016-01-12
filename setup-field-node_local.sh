#!/bin/bash

set -e -o pipefail

apt-get install -y ansible

ansible-playbook ./field-node/node-base.yml -i ./production --connection=local --sudo -vvvv
