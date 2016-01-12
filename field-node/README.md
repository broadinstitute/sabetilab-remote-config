## setup

### Prior to field deplyment

On the field node machine, run ansible on the playbook (relative to the field-node directory:

```
ansible -i ../production ./node-base.yml --connection=local --sudo -vvvv
```

Append the ssh key for the SSH reverse tunnel from the field node:

`/home/autossh/.ssh/id_rsa.pub`

to the manager node key list:

`/home/autossh/.ssh/authorized_keys`

Ensure the authorized_keys file has the correct permissions:

`chmod 644 /home/autossh/.ssh/authorized_keys`

Be default, the SSH daemon of the field nodes listens on port `6112`.