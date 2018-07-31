#!/usr/bin/python

import re, sys
import os
import json
import subprocess
from collections import defaultdict

import yaml

class AnsibleInventory(object):
    def __init__(self, local=False):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings_manager.yml"), "r") as settings_file:
           self.settings_object = yaml.load(settings_file)

        self.domain  = self.settings_object["domain_name"]
        self.manager_domain = "manager." + self.domain
        self.username = self.settings_object["ssh_username"]


        if not local:
            nodes = {
                "hosts"   : self.settings_object["connected_nodes"],
                "vars"    : {
                    "ansible_ssh_common_args": '-o ProxyCommand="ssh -W %h:%p {user}@{manager}"'.format(user=self.username, manager=self.manager_domain),
                    "ansible_host"           : "localhost",
                    "ansible_user"           : "{user}".format(user=self.username),
                    "ssh_port"               : "6112"
                }
            }
        else:
            nodes = {
                "hosts" : ["localhost"],
                "vars" : {
                    "ansible_connection" : "local"
                }
            }

        # base inventory
        self.inventory = {
            "nodes"   : nodes,
            "managers"    : [ self.manager_domain ],
            "_meta" : {
                  "hostvars" : {}
               }
        }

        if not local:
            self._populate_host_ports()

        self._populate_vars_from_settings()

    @staticmethod
    def _get_txt_record_from_dns(fqdn):
        #return subprocess.check_output(['dig', '-t', 'TXT', fqdn, '+short'])
        return subprocess.check_output(['dig', '-t', 'TXT', fqdn, '@ns-491.awsdns-61.com', '+short'])

    @staticmethod
    def _get_port_from_txt_record(txt_record):
        port_num_matches = re.findall(r'^"?P(\d+).*;.*"?$', txt_record.decode("utf-8"))
        port_num = ""
        if len(port_num_matches) > 0:
            port_num = port_num_matches[0]
        else:
            raise KeyError("No port found in TXT record: %s" % txt_record)

        return port_num

    def _populate_host_ports(self):
        for node_hostname in self.inventory["nodes"]["hosts"]:
            node_fqdn = node_hostname + "." + self.domain
            port_for_node = self._get_port_from_txt_record(self._get_txt_record_from_dns(node_fqdn))

            self.inventory["_meta"]["hostvars"].setdefault(node_hostname, dict())
            self.inventory["_meta"]["hostvars"][node_hostname]["ansible_port"] = port_for_node

    def _populate_vars_from_settings(self):
        # populate host vars
        if "extra_host_vars" in self.settings_object:
            for hostname in self.settings_object["extra_host_vars"].keys():
                if hostname in self.inventory["nodes"]["hosts"]:
                    self.inventory["_meta"]["hostvars"].setdefault(hostname, dict())    
                    self.inventory["_meta"]["hostvars"][hostname].update(self.settings_object["extra_host_vars"][hostname].copy())

        # populate group vars
        if "extra_group_vars" in self.settings_object:
            for groupname in self.settings_object["extra_group_vars"].keys():
                if groupname in self.inventory:
                    self.inventory[groupname].setdefault("vars", dict())
                    self.inventory[groupname]["vars"].update(self.settings_object["extra_group_vars"][groupname].copy())

    @staticmethod
    def dump_json(obj_to_dump):
        return json.dumps(obj_to_dump, sort_keys=True, indent=4, separators=(',', ': '))


    def grouplist(self):
        return self.dump_json(self.inventory)

    def hostinfo(self):
        return self.dump_json({})
    
if __name__ == '__main__':
    inv = AnsibleInventory(local=True if os.environ.get("LOCAL_ANSIBLE","").lower()=="true" else False)

    if len(sys.argv) == 2 and (sys.argv[1] == '--list'):
        print(inv.grouplist())
    elif len(sys.argv) == 3 and (sys.argv[1] == '--host'):
        # Not implemented since we return info for all hosts in one call via --list.
        # Using --host is slower, older, and likely to be deprecated.
        print(inv.dump_json({}))
    else:
        print("Usage: %s --list or --host <hostname>" % sys.argv[0])
        sys.exit(1)
