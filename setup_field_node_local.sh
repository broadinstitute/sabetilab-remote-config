#!/bin/bash

set -e -o pipefail

apt-get install -y ansible

echo ""
echo "========================================================"
read -p "Enter would you like the hostname of this machine to be ($(hostname)): " NODEHOSTNAME

if [[ -z $NODEHOSTNAME ]]; then
    echo "keeping the same hostname: $(hostname)"
else
    echo "127.0.0.1    localhost.localdomain localhost" > /etc/hosts
    echo "127.0.1.1    $NODEHOSTNAME" >> /etc/hosts
    echo "" >> /etc/hosts
    hostnamectl set-hostname $NODEHOSTNAME
fi

ansible-playbook ./field-node/node-base.yml -i ./production --connection=local --sudo -vvvv