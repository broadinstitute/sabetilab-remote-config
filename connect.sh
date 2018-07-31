#!/bin/bash

set -e -o pipefail

if [[ "$#" -ne 1 && "$#" -ne 2 ]]; then
    echo "Usage: $(basename $0) subdomain.domain.tld [github_username]"
    exit 1
fi

SCRIPT_DIRECTORY=$(dirname $0)

NODE_DOMAIN=$1
#RELAY_DOMAIN=""

RELAY_DOMAIN=$(cat $SCRIPT_DIRECTORY/settings_field_node.yml | grep "manager_domain_name" | perl -lape 's/(.*):\s*(\S*)/$2/g')

CONNECT_USERNAME=""
if [[ ! -z "$2" && "$2" != " " ]]; then
    CONNECT_USERNAME=$2
else
    CONNECT_USERNAME="$(whoami)"
fi

# get the IP of the manager node
# use the AWS nameserver to ensure most current DNS records
MANAGER_IP=$(dig A +short $RELAY_DOMAIN @ns-491.awsdns-61.com)

# get the port from the DNS TXT record for this subdomain
# use the AWS nameserver to ensure most current DNS records
PORT_ON_RELAY=$(dig TXT +short $NODE_DOMAIN @ns-491.awsdns-61.com | perl -lape 's/^"P(?<port_num>[0-9]+).*"/$+{port_num}/g')

if [[ -z "$PORT_ON_RELAY" || "$PORT_ON_RELAY" == " " ]]; then
        echo "The TXT record for the subdomain specified does begin have a ^PNNN; ... entry"
        exit 1
fi

echo "Connecting to '$NODE_DOMAIN' via local port '$PORT_ON_RELAY' on relay '$RELAY_DOMAIN'"
echo ""
echo "Note: a live reverse tunnel must be present between '$NODE_DOMAIN' and '$RELAY_DOMAIN'"
echo "      binding the SSH port of '$NODE_DOMAIN' to the local port '$PORT_ON_RELAY' on '$RELAY_DOMAIN.'"
echo ""

echo "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ProxyCommand=\"ssh -W %h:%p $CONNECT_USERNAME@$MANAGER_IP\" $CONNECT_USERNAME@localhost -p $PORT_ON_RELAY"
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ProxyCommand="ssh -W %h:%p $CONNECT_USERNAME@$MANAGER_IP" $CONNECT_USERNAME@localhost -p "$PORT_ON_RELAY"

