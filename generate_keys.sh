#!/bin/bash

set -e -o pipefail

KEY_DIRECTORY=$(dirname $0)/keys
AUTOSSH_KEY_PREFIX="autossh_id_rsa"
GITHUB_KEY_PREFIX="github_deploy_read_only_id_rsa"

echo $KEY_DIRECTORY

mkdir -p $KEY_DIRECTORY

echo "Generating SSH keys (this may take a moment)..."

# generate autossh tunnel keys and save to ./files/
# as autossh_id_rsa and autossh_id_rsa.pub
# option to generate without prompt for passkey?
ssh-keygen -t rsa -b 4096 -C "autossh_tunnel_key" -N '' -f $KEY_DIRECTORY/$AUTOSSH_KEY_PREFIX

# generate GitHub deployment keys
# as github_deploy_read_only_id_rsa(.pub)
# ssh-keygen -t rsa -b 4096 -C "github_deploy_read_only_id_rsa" -N '' -f $KEY_DIRECTORY/$GITHUB_KEY_PREFIX
# echo ""
# echo " ==================================================================================================="
# echo "  Important! Be sure to copy the GitHub public key to the deployment keys section of this repository!"
# echo "  It is located here: "
# echo "    $KEY_DIRECTORY/$GITHUB_KEY_PREFIX.pub"
# echo "  The public key is:"
# echo ""
# cat $KEY_DIRECTORY/$GITHUB_KEY_PREFIX.pub
# echo ""


cd $KEY_DIRECTORY && wget http://sensuapp.org/docs/0.21/tools/ssl_certs.tar -O sensu_ssl_certs.tar && tar -xvf sensu_ssl_certs.tar && rm sensu_ssl_certs.tar && mv ssl_certs sensu_ssl_certs

cd sensu_ssl_certs && ./ssl_certs.sh generate
