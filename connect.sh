#!/bin/bash

set -e -o pipefail

DOMAIN="wmc07-f52.sabeti-aws.net"

# get the port from the DNS TXT record for this subdomain
PORT=$(dig TXT +short $DOMAIN @ns-491.awsdns-61.com | awk -F'"' '{ print $2}' | perl -lape 's/^P([0-9]+)\\.*/$1/g')

ssh -o ProxyCommand='ssh -W %h:%p manager' $DOMAIN
