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

apt-get install -y ansible openssh-server

SCRIPT_DIRECTORY=$(dirname $0)
SETTINGS_YML="settings_field_node.yml"

DOMAIN_NAME=$(cat $SCRIPT_DIRECTORY/$SETTINGS_YML | grep "^domain_name" | perl -lape 's/(.*):\s*(\S*)/$2/g')

REMOTE_LISTEN_PORT=$(( ( RANDOM % 1000 )  + 32000 )) # pick a random port in the range [32000,32000]

# make dynamic-inventory.py executable
chmod +x $SCRIPT_DIRECTORY/dynamic-inventory.py

echo "Domain parsed from $SETTINGS_YML as \"$DOMAIN_NAME\""
echo ""
echo "========================================================"
DEFAULT_SSH_PORT=6112
read -p "Enter the node SSH daemon listen port [$DEFAULT_SSH_PORT]: " SSH_PORT
SSH_PORT=${SSH_PORT:-"$DEFAULT_SSH_PORT"} # set default if not specified

read -p "Enter the SSH tunnel port to be accessed on the relay (default:0[dynamic]): " SSH_TUNNEL_PORT
SSH_TUNNEL_PORT=${SSH_TUNNEL_PORT:-"0"}

read -p "Enter would you like the hostname of this machine to be [$(hostname)]: " NODEHOSTNAME
NODEHOSTNAME=${NODEHOSTNAME:-"$(hostname)"}

if [[ -z $NODEHOSTNAME ]]; then
    echo "keeping the same hostname: $(hostname)"
    NODEHOSTNAME="$(hostname)"
fi

echo ""
echo "The hostname of this machine will be: \"$NODEHOSTNAME\""
echo "The FQDN of this machine will be: \"$NODEHOSTNAME.$DOMAIN_NAME\""
echo "The SSH daemon will listen on port: $SSH_PORT"
echo "This node can be reached via the manager node on its local port $SSH_TUNNEL_PORT"
echo ""

read -p "Press [ENTER] to configure this machine, or [Control+C] to cancel"

echo "127.0.0.1    localhost.localdomain localhost" > /etc/hosts
echo "127.0.1.1    $NODEHOSTNAME.$DOMAIN_NAME $NODEHOSTNAME" >> /etc/hosts
echo "" >> /etc/hosts
hostnamectl set-hostname $NODEHOSTNAME
#grep "Domains=$DOMAIN_NAME" /etc/systemd/resolv.conf || echo "Domains=$DOMAIN_NAME" >> /etc/systemd/resolv.conf
pushd /etc/systemd > /dev/null
sed -E -i.bak "s/\#Domains=/Domains=/g" /etc/systemd/resolved.conf && rm resolved.conf.bak
sed -E -i.bak "/Domains=/s/([ ]?$DOMAIN_NAME[ ]?)//g" /etc/systemd/resolved.conf && rm resolved.conf.bak
sed -E -i.bak "s/(Domains=)([^\n]*)/\1$DOMAIN_NAME \2/g" /etc/systemd/resolved.conf && rm resolved.conf.bak
popd > /dev/null

#ansible-playbook ./field-node/node-full.yml -i dynamic-inventory.py --connection=local --sudo # -vvvv
ansible-playbook ./field-node/node-full.yml -i dynamic-inventory.py --connection=local --limit $NODEHOSTNAME --become --extra-vars="ssh_port=$SSH_PORT ssh_tunnel_port=$SSH_TUNNEL_PORT"
