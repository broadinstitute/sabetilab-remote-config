#!/bin/bash

set -e -o pipefail

ROOT_UID="0"
#Check if run as root
if [[ "$UID" -ne "$ROOT_UID" ]] ; then
    echo "You must use sudo or be root!"
    sudo -k # invalidates cached credentials, causing re-prompt
    sudo $0 # re-execute self
    exit 1
fi

apt-get install -y ansible

SCRIPT_DIRECTORY=$(dirname $0)
SETTINGS_YML="settings_field_node.yml"

DOMAIN_NAME=$(cat $SCRIPT_DIRECTORY/$SETTINGS_YML | grep "^domain_name" | perl -lape 's/(.*):\s*(\S*)/$2/g')

REMOTE_LISTEN_PORT=$(( ( RANDOM % 1000 )  + 32000 )) # pick a random port in the range [32000,32000]

echo "Domain parsed from $SETTINGS_YML as \"$DOMAIN_NAME\""
echo ""
echo "========================================================"
read -p "Enter the node SSH daemon listen port [22]: " SSH_PORT
SSH_PORT=${SSH_PORT:-"22"} # set default if not specified

read -p "Enter the SSH tunnel port to be accessed on the relay [$REMOTE_LISTEN_PORT]: " SSH_TUNNEL_PORT
SSH_TUNNEL_PORT=${SSH_TUNNEL_PORT:-"$REMOTE_LISTEN_PORT"}

read -p "Enter would you like the hostname of this machine to be [$(hostname)]: " NODEHOSTNAME
NODEHOSTNAME=${NODEHOSTNAME:-"$(hostname)"}

if [[ -z $NODEHOSTNAME ]]; then
    echo "keeping the same hostname: $(hostname)"
    NODEHOSTNAME="$(hostname)"
fi
echo "127.0.0.1    localhost.localdomain localhost" > /etc/hosts
echo "127.0.1.1    $NODEHOSTNAME.$DOMAIN_NAME $NODEHOSTNAME" >> /etc/hosts
echo "" >> /etc/hosts
hostnamectl set-hostname $NODEHOSTNAME
grep "search $DOMAIN_NAME" /etc/resolvconf/resolv.conf.d/base || echo "search $DOMAIN_NAME" >> /etc/resolvconf/resolv.conf.d/base

echo ""
echo "The hostname of this machine is: \"$NODEHOSTNAME\""
echo "The FQDN of this machine is: \"$NODEHOSTNAME.$DOMAIN_NAME\""
echo "The SSH daemon will listen on port: $SSH_PORT"
echo "This node can be reached via the manager node on its local port $SSH_TUNNEL_PORT"
echo ""

read -p "Press [ENTER] to configure this machine, or [Control+C] to cancel"

#ansible-playbook ./field-node/node-base.yml -i ./production --connection=local --sudo # -vvvv
ansible-playbook ./field-node/node-base.yml -i "[nodes]localhost," --connection=local --sudo --extra-vars="ssh_port=$SSH_PORT ssh_tunnel_port=$SSH_TUNNEL_PORT"