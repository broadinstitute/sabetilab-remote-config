## Installation of requirements:

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

## Configuration
Create an AWS IAM user with EC2 and Route53 permissions.

Create a Route53 A record for the subdomain to be used for the management node (vagrant-aws-route53 can updatethe record but not create it).

Create an SSH key pair for accessing EC2 instances, copying the *.pem file to a known location, and change its permissions: `chmod 400`

Ensure the default EC2 security group permits inbound SSH connections on port 22 from anywhere.

Create a new `settings.yml` in this directory, based on `settings.yml.template`

Set the values specified in settings.yml

## Running
`cd management-node`

To provision the manager node for the first time:
`vagrant up`

To reprovision the manager node:

`vagrant provision`

To connect to the manager node:

`vagrant ssh`

An EC2 instance for the management node will be created. The IP address will be assigned to the subdomain of the domain name specified in `settings.yml`.

The manager node creates users 

By default, SSH public keys are copied`github_usernames_with_access` and `github_usernames_with_sudo_access`