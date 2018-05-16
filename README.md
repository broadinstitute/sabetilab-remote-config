[![Build Status](https://travis-ci.com/broadinstitute/sabetilab-remote-config.svg?token=MpDq9eJxuo1jZsXqvFHq&branch=master)](https://travis-ci.org/broadinstitute/sabetilab-remote-config)

# sabetilab-remote-config
remote configuration files for systems at African field sites

## Description

## Install dependencies

### Local machine

* Install PyYAML

`pip install PyYAML`

* Install [vagrant](https://www.vagrantup.com/)

`brew install vangrant`

or

`apt-get install vagrant`

* Install [ansible](http://www.ansible.com/)

`brew install ansible`

or

`apt-get install ansible`

* `vagrant-aws`

`vagrant plugin install vagrant-aws`

* `vagrant-aws-route53`

`vagrant plugin install vagrant-aws-route53`

## setup

### Initial configuration

Clone this repository from GitHub to your machine.

`git clone https://github.com/broadinstitute/sabetilab-remote-config.git`

Create a new `settings_manager.yml` in the root-level repo directory, based on `settings_manager.yml.template`. Also create a new `settings_field_node.yml` in this directory, based on `settings_field_node.yml.template`

Create an AWS IAM user with EC2 and Route53 permissions, and save the credentials. Use the key and secret in configuring `settings_manager.yml`. Create a second set of AWS credentials with only Route53 permissions, and use the values in configuring `settings_field_node.yml`.

Create a Route53 A record for the subdomain to be used for the management node (vagrant-aws-route53 can update the record but not create it).  The name `manager`.example.com is suggested. This record can be created via the AWS web console.

Create an AWS SSH key pair for accessing EC2 instances, copy the *.pem file to a known location (`~/.ssh/` is suggested), and change its permissions: `chmod 600` This key can be created via the AWS web console.

Ensure the default EC2 security group permits inbound SSH connections on TCP ports {22,6112} from anywhere. If you wish to use monitoring, also add TCP ports {3000,5671,5672}. The IP range for SSH and monitoring must be set to "Anywhere" (0.0.0.0), while port 3000 may be restricted as it serves the monitoring web interface (CIDR for the Broad Institute: 69.173.64.0/18).

Set the values specified in `settings_manager.yml` and `settings_field_node.yml`.

Run the following script to create SSH keys to be used for the reverse tunnel:

`./generate_keys.sh`

**Note:** If you do not have any public key pairs associated with yout GitHub account, you will need to generate a new pair and as [described here](https://help.github.com/articles/generating-ssh-keys/), and [add the public key to your GitHub profile](https://github.com/settings/ssh). This will allow you to authenticate directly into the management node and the field nodes, as long as the private key is present and configured in `~/.ssh/`.

### Set up the manager

From the local machine, deploy the manager by calling:

`./setup_manager.sh`

This helper script will use Vagrant to initialize an EC2 instances which will then be configured via Ansible. It will also update the Route53 `A` record for the manager to have the correct IP address for the instance. After the manager has been set up, you will be able to connect to it directly via SSH (detailed below).

To enable monitoring:

manually ssh to the machine `ssh manager.example.com` and set your root password if prompted, then:

`ansible-playbook -i dynamic-inventory.py --become --ask-become-pass management-node/manager-sensu.yml`

### Set up the field nodes

The field nodes should be running Ubuntu 15.10. If hibernation ability is desired, ensure the machine is capable (via `pm-hibernate`), that the Product Name (via `dmidecode -s system-product-name`) is listed in `node-enable-hibernate.yml`, and ensure the swap partition size is larger than the physical RAM capacity. 
Install the operating system and pick a hostname. The hostname will become the subdomain automatically given to the field node, and should match an entry found in the settings file, `settings_manager.sh`, under `connected_nodes`. It may be desirable to enable "Wake on AC" in the BIOS options if such an option is available.

**Note:** Ubuntu 16.04 LTS is currently incompatible due to a [known kernel bug that breaks hibernation](https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1566302). If/when the kernel bug is fixed, version 16.04 and later may be supported. Versions earlier than 15.10 are unsupported.

Using a USB thumbdrive or similar, copy the entire local checkout of this repository to each field node (including the settings files and tunnel keys). 
 
On each field node, run:

`sudo ./setup_field_node_local.sh`

To enable monitoring:

`ansible-playbook ./field-node/node-sensu.yml -i local_inventory_nodes --become --ask-become-pass`

From remote:

`ansible-playbook -i dynamic-inventory.py --become --ask-become-pass ./field-node/node-sensu.yml`

#### Samba shares

As part of the setup process, a samba/CIFS user will be created (ex. "miseq", or whatever you specify when prompted) on the field node. A shared directory for this user will be created on the field node upon first log-in by the user, located at `/srv/samba/home/<samba_username>`.

#### DNAnexus upload

There is a playbook, `field-node/node-dx-uploader.yml`, that makes use of the DNAnexus [role](https://github.com/dnanexus-rnd/dx-streaming-upload) to stream data from a samba share to a project on DNAnexus. Once configured, any MiSeq run directories copied to the samba share of a field node will be automatically uploaded to DNAnexus.

To configure for automated uploads, a project needs to be created on DNAnexus. A user should be created to be used with the uploader.  The project should be read-only for all users but one created specifically to handle uploads. This ensures that the file structure of the project on the cloud side remains inline with what is expected by the DNAnexus upload client.

After a project and upload user have been created, a DNAnexus API token should be created for the upload user. 

The DNAnexus project ID ("`project-aaabbbccc...`") and user API token must be copied to Ansible variables, and an applet ID ("`applet-aaabbbccc...`") may optionally be specified. If it is desired to use the same project and user for all nodes, modify the `extra_group_vars` section within `settings_manager.yml` to hold the values to use for all nodes. If a node-specific upload user or project is preferred, the group settings can be overridden by modifying the `extra_host_vars` section within `settings_manager.yml`.

After the project and user have been created, and the values have been set in `settings_manager.yml`, the playbook to set up the uploader can be run on the field nodes. 

**Note:** This playbook must be run AFTER a samba user has been created by `field-node/node-samba.yml`. A samba user should already exist if the field node was configured via `setup_field_node_local.sh` or by running the playbook `field-node/node-full.yml`. The playbook will prompt for the samba username of the user to sync to DNAnexus. In most cases this should be the samba user created earlier in the configuration process.

`ansible-playbook ./field-node/node-dx-uploader.yml -i local_inventory_nodes --become --ask-become-pass`

From remote:

`ansible-playbook -i dynamic-inventory.py --become --ask-become-pass field-node/node-dx-uploader.yml`

## Making changes

To perform an `apt-get update` and `apt-get upgrade` on the management node and each of the field nodes:

`ansible-playbook -i dynamic-inventory.py --become --ask-become-pass common-playbooks/update-upgrade-apt-packages.yml`

### management node

To apply changes to the management node, it must be reprovisioned:

`cd ./management-node && vagrant provision`

An EC2 instance for the management node will be created. The IP address will be updated on the domain record for the subdomain of the domain name specified in `settings_manager.yml`.

To issue ad hoc commands to the management node, ensure the address is listed in `./production`, then run:

`ansible managers -i ./dynamic-inventory.py -m shell -a "date"`

To run a playbook on the management node:

`ansible-playbook -i ./dynamic-inventory.py [--become --ask-become-pass] some-playbook.yml`

### field node

Before running remote Ansible commands on the nodes, make sure you can connect to each of the nodes and have set your password (sudoers only). Sudoers will be prompted to set their password upon first connect:

`./connect.sh node-name.example.com [github_username]`

To issue one-off ansible commands to the nodes:

`ansible nodes -i dynamic-inventory.py [--become --ask-become-pass] -m shell -a "some_command"`

Or for one node:

`ansible node-3 -i dynamic-inventory.py [--become --ask-become-pass] -m shell -a "some_command"`

To run a playbook on all nodes (restricted by hosts in playbook):

`ansible-playbook -i dynamic-inventory.py [--become --ask-become-pass] some-playbook.yml`

To run a playbook on one node:

`ansible-playbook --limit node-3 -i dynamic-inventory.py [--become --ask-become-pass] some-playbook.yml`

To reboot all nodes (note that this command may appear to fail, since a reboot prevents Ansible from receiving confirmation of command execution):

`ansible nodes -i dynamic-inventory.py --become --ask-become-pass -m shell -a "reboot"`

To re-provision the field nodes from their full setup playbook:

`ansible-playbook -i dynamic-inventory.py --become --ask-become-pass field-node/node-full.yml`

The following field node playbooks exist and may be used for more directed configuration changes:
* `field-node/node-full.yml` (complete setup of field nodes including playbooks below)
* `field-node/node-base.yml` installs dependencies and configures SSH daemon
* `field-node/node-users.yml` creates users specified in `settings_field_node.yml` and adds their github keys as appropriate
* `field-node/node-samba.yml` installs and configures samba server, adds samba user
* `field-node/node-tunnel.yml` installs autossh and configures SSH reverse tunnel
* `field-node/node-restart-autossh.yml` restarts the autossh daemon
* `field-node/node-sensu.yml` sets up monitoring on the field node
* `field-node/node-dx-uploader.yml` sets up streaming upload to DNAnexus
* `field-node/node-geoip.yml` prints the geographic location of each node
* `field-node/compile-and-install-python.yml` This builds and installs Python 2.7.x from source
* `field-node/node-set-sources-list-to-old-release.yaml` For End-of-Life Ubuntu releases, this updates the apt-source list to use the old-releases source repository

## Setup in the field

### Network configuration
Each field node expects to share a subnet with the devices that will be uploading data. Consequently, a field node and its MiSeq instruments will need to be connected to a common router:

                      ╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳                       
                     ╳          Internet          ╳                      
                      ╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳                       
                                    ▲                                    
                                    │                                    
                                    ▼                                    
                        ┌───────────────────────┐                        
                        │   Institutional LAN   │                        
                        │        or ISP         │                        
                        └───────────────────────┘                        
                                    ▲                                    
                                    │                                    
                                    ▼                                    
                        ┌───────────────────────┐                        
    ┌───────────────────┤        Router         ├──────────────────────┐ 
    │                   └──▲────────▲─────▲─────┘                      │ 
    │              ┌───────┘        │     └─────────────┐              │ 
    │              ▼                │                   │              │ 
    │  ┌───────────────────────┐    └────┐              ▼              │ 
    │  │      Field node       │         │  ┌───────────────────────┐  │ 
    │  └───────────────────────┘         │  │         MiSeq         │  │ 
    │                                    │  └───────────────────────┘  │ 
    │                                    ▼                             │ 
    │                                  ┌───────────────────────┐       │ 
    │                                  │         MiSeq         │       │ 
    │                                  └───────────────────────┘       │ 
    └────────────────────────────────────────────────Shared subnet─────┘ 

### Software configuration

#### MiSeq setup
The location of the run directory used by each MiSeq should be set to be the samba share. Once connected to a common router, the samba share provided by the field node should be visible to the MiSeq via Explorer as a network drive. On the MiSeq, mount the samba share, entering the samba username and credentials specified when the field node was configured.

## Connecting to nodes

```
                                            ┌─┐                      
                                            │ │                      
                                            │ │                      
┌─────────────┐        ┌─────────────┐      │ │       ┌─────────────┐
│    local    │        │    relay    │      │ │       │   remote    │
│   machine   │◀──────▶│   machine   │◀─────┼─┼───────│   machine   │
└─────────────┘        └─────────────┘      │ │       └─────────────┘
                                            │ │                      
                                            │ │                      
                                            │ │                      
                                            │ │                      
                                            └─┘                      
                                       NAT/firewall                  
```

The system configuration relies on the management node to serve as an SSH relay for nodes deployed in the field. Field nodes open an SSH reverse tunnel that fowards local ports to the management node to the SSH ports of the field nodes. This tunnel allows communication with the field nodes, even if they are behind firewall or NAT, as long as they are permitted to make outbound SSH connections. The reverse tunnel setup assumes the management node has been configured to accept inbound SSH connections on port 22, and that the field nodes are allowed to make outbound SSH connections to the Internet on port 22. The field nodes *do* listen for inbound SSH connections, on port 6112.

### management node

Assuming your github username has been specified prior to provisioning, you can connect to the management node directly using your own SSH credentials:

`ssh github_username@manager.example.net`

If for some reason you need to connect using the AWS key pair, `cd ./management-node` then call:

`vagrant ssh`

### field nodes

You may be able to connect to field nodes directly via ssh if they are not located behind firewall or NAT. By default the field nodes run their SSH daemon on port 6112.

`ssh github_username@node-name.example.com -p 6112`

If the field node is behind NAT or a firewall that blocks inbound SSH connections, you can connect to it via its reverse tunnel connection to the manager node. A helper script makes this simple:

`./connect.sh node-name.example.com [github_username]`

Since the tunnel port on the manager varies, the helper script identifies the correct port by examining a note published as part of the DNS TXT record for the node.

**Node:** If the private key files for the public keys published by github are not named according to a pattern normally searched by ssh (`id_rsa`, etc.), you will need to add an entry to `~/.ssh/config` to specify the correct key file for the domain name specified in `settings_manager.yml`. Ex.

    Host *.example.com
        IdentityFile ~/.ssh/my_id_rsa

**Note 2:** Manually changing the system configuration of the field nodes is discouraged. Ideally all changes to the field nodes should be encapsulated as version-controlled ansible playbooks for repeatability.

You can connect to the manager node directly, and then connect to the correct port at localhost on the management node (keys will need to be present on the manager and field nodes):

`ssh localhost -p PORTNUM`

When connected to the manager, to see a list of remote IPs and the corresponding local ports they have tunnels to:

```bash
sudo lsof -i -n | egrep '\<sshd\>' | grep -v ":ssh" | grep LISTEN | sed 1~2d | awk '{ print $2}' | while read line; do sudo lsof -i -n | egrep $line | sed 3~3d | sed 's/.*->//' | sed 's/:......*(ESTABLISHED)//' | sed 's/.*://' | sed 's/(.*//' | sed 'N;s/\n/:/' 2>&1 ;done
```

## Notes

If you have difficulty connecting to the manager via ssh, or if it prompts repeatedly for a password change ensure you do not have `ControlMaster auto` set in `~/.ssh/config`.

When running Ansible playbooks on the nodes, if you receive errors along the lines of "Connection timed out during banner exchange", try adding the following to `~/.ssh/config`:
```bash
ControlMaster auto
ControlPath ~/.ssh/ssh_control_%h_%p_%r
ControlPersist 10m
```

Note that the username to be used for ansible connections must be specified in `settings_manager.yml`. Any ansible playbooks run with ``--become`` must use this same user, and the sudo password must be the same across all nodes on which the playbook is to be run. In must cases the user should be one present in `github_usernames_with_sudo_access`.

In the event an exfat USB drive is not mounting, run `fusermount -u /media/broken-mount-point`. If this does not work, try `systemctl reset-failed` if "Unit is bound to inactive unit dev-disk-by" is present in `/var/log/syslog`. In the event that the drive is disconnected without being properly ejected, fuse-exfat, and the drive, may have issues. To repair, plug into an OSX machine and run `sudo fsck_exfat -d <diskID_here>`. OSX may detect the drive has not been properly ejected and run fsck automatically. This can be checked by running `sudo lsof | grep <diskID_here>`. 

If time-rotated moves to external storage is desired, the external drive should be formatted ExFAT, and the drive name (label) should be `SEQDATA`.

To reach the router used by the field machines (ex. 192.168.2.1), add a local port forward `-L 8080:192.168.2.1:443` and access `localhost:8080` on the initiating machine via a web browser:

    ssh -L 8080:192.168.2.1:443 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ProxyCommand= [...]

The local port forward can be added to the command printed by `./connect.sh` 

### management node

As an alternative to the `setup-manager.sh` script, the management node can be deployed by calling vagrant directly:

`vagrant up`

### field nodes

In debugging the samba shared drive, the following commands can be helpful when run on a field node:

List active samba connections to the samba server:
`sudo smbstatus -b`

View samba mount from localhost:
```
smbclient -U <samba_username>  //<hostname>/miseq
# (enter password and 'ls')
```
