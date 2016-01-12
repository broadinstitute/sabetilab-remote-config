[![Build Status](https://travis-ci.com/broadinstitute/sabetilab-remote-config.svg?token=MpDq9eJxuo1jZsXqvFHq&branch=master)](https://travis-ci.org/broadinstitute/sabetilab-remote-config)

# sabetilab-remote-config
remote configuration files for systems at African field sites

## setup

## Uage

### Connection prerequisites (SSH)

Both the manager node and the field nodes are set up to 

### Making

Connecting to a remote field node via the relay server:

```
ssh -o ProxyCommand='ssh -W %h:%p user1@manager' user1@node
```