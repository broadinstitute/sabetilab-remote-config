#!/bin/bash

set -e -o pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $(basename $0) subdomain.domain.tld"
    exit 1
fi

SCRIPT_DIRECTORY=$(dirname $0)

DOMAIN=$1
#RELAY_DOMAIN=""

RELAY_DOMAIN=$(cat $SCRIPT_DIRECTORY/settings_field_node.yml | grep "manager_domain_name" | perl -lape 's/(.*):\s*(\S*)/$2/g')

# get the IP of the manager node
# use the AWS nameserver to ensure most current DNS records
MANAGER_IP=$(dig A +short $RELAY_DOMAIN @ns-491.awsdns-61.com)

# get the port from the DNS TXT record for this subdomain
# use the AWS nameserver to ensure most current DNS records
PORT=$(dig TXT +short $DOMAIN @ns-491.awsdns-61.com | awk -F'"' '{ print $2}' | perl -lape 's/^P([0-9]+)\\.*/$1/g')

echo "Connecting to '$DOMAIN' via local port '$PORT' on relay '$RELAY_DOMAIN'"
echo ""
echo "Note: a live reverse tunnel must be present between '$DOMAIN' and '$RELAY_DOMAIN'"
echo "      binding the SSH port of '$DOMAIN' to the local port '$PORT' on '$RELAY_DOMAIN.'"
echo ""

if [[ -z "$PORT" || "$PORT" == " " ]]; then
        echo "The TXT record for the subdomain specified does begin have a ^PNNN; ... entry"
        exit 1
fi

echo "ssh -o ProxyCommand=\"ssh -W %h:%p $MANAGER_IP\" localhost -p $PORT"

ssh -o ProxyCommand="ssh -W %h:%p $MANAGER_IP" localhost -p "$PORT"