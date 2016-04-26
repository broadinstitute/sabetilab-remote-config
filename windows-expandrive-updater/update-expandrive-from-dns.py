#!/usr/bin/python

import os,sys,re,shutil
import subprocess
import json
import random
from os.path import exists

from datetime import datetime

import psutil
import yaml # pip install PyYAML
import boto
import boto.route53 # pip install boto==2.39.0
import boto.cacerts
from dateutil.parser import parse as parsedate #python-dateutil

aws_access_key_id = ""
aws_secret_access_key = ""
hosted_zone_domain_name = "example.net"
# must have trailing period
hosted_zone_domain_name = hosted_zone_domain_name + "." if hosted_zone_domain_name[-1] != "." else hosted_zone_domain_name

# For Windows 10

# IAM policy should be something like:
# intended to be packed via py2exe (python setup.py py2exe)
'''
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Stmt1461611100000",
                "Effect": "Allow",
                "Action": [
                    "route53:ListResourceRecordSets"
                ],
                "Resource": [
                    "arn:aws:route53:::hostedzone/Zxxxxxxxxxxxxx"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "route53:ListHostedZones"
                ],
                "Resource": "*"
            }
        ]
    }
'''

def get_port(txt_record):
    port_num_matches = re.findall('^P(\d+);.*', txt_record)
    port_num = ""
    if len(port_num_matches) > 0:
        port_num = port_num_matches[0]

    return port_num

def get_datetime(txt_record):
    datetime_string_matches = re.findall('^.*Last update (.*)\.', txt_record)
    date = ""
    if len(datetime_string_matches) > 0:
        date = datetime_string_matches[0]

    return parsedate(date)

def get_nodes():
    print("Updating field node information...")
    nodes = []

    bt = boto
    conn = bt.route53.connection.Route53Connection(aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)#, validate_certs="boto\cacerts\cacerts.txt")
    conn.ca_certificates_file = "boto\cacerts\cacerts.txt"
    zone = conn.get_zone(hosted_zone_domain_name)
    records = [r for r in conn.get_all_rrsets(zone.id)]

    for rec in records:
        if rec.type == "TXT":
            txt_rec_value = rec.resource_records[0].strip('"')
            hostname = rec.name.split(".")[0]
            port = get_port( txt_rec_value )
            date = get_datetime( txt_rec_value )
            secs_since_update = (datetime.utcnow()-date).total_seconds()

            node = {}
            node["hostname"] = hostname
            node["port"] = port
            node["date"] = date
            node["secs_since_update"] = secs_since_update
            
            if port:
                nodes.append(node)
    print("Field node information update complete.")
    return nodes

def create_expandrive_server(server_address, username, remote_path, nickname, port):
    record = {
        "server": server_address,
        "username": username,
        "remotePath": remote_path,
        "encryptedPassword": "AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAtOz/p0N+vUCRq2sMUq5GXAAAAAACAAAAAAADZgAAwAAAABAAAAC7oxUuuY+ebtRVXco5/39zAAAAAASAAACgAAAAEAAAAHQLmw6OcYkwa5fjB5oSpawIAAAAMqyA052QYlcUAAAA6LmoUgXw3e3GUdhbkZGyg2bTXew=",
        "type": "sftp",
        "protocol": "sftp",
        "name": nickname,
        "port": port,
        "reconnectAtLogon": False,
        "authentication": "pageant",
        "private_key_file": None,
        "position": 2,
        "mountpoint": "Z:",
        "id": "".join([chr(i) for i in random.sample(range(ord('a'), ord('z')+1),7)])
    }
    return record


def kill_process(process_name):
    print("Killing", process_name)
    for proc in psutil.process_iter():
        if proc.name() == process_name:
            proc.kill()

def start_process(executable):
    print("Starting", executable)
    subprocess.Popen([executable], creationflags=subprocess.CREATE_NEW_CONSOLE )

if __name__ == "__main__":
    #print(get_nodes())
    expandrive_executable = "C:\Program Files (x86)\ExpanDrive\ExpanDrive.exe"
    if exists(expandrive_executable):
        print("Expandrive present")

        # kill expandrive
        kill_process("ExpanDrive.exe")

        settings_file = os.path.join( os.path.dirname(os.path.expandvars('%APPDATA%')), "Local", "ExpanDrive", "expandrive5.favorites.js" )
        settings_file_modified = os.path.join( os.path.dirname(os.path.expandvars('%APPDATA%')), "Local", "ExpanDrive", "expandrive5.favorites.js.mod" )

        #print(settings_file)
        if exists(settings_file):
            servers = []
            for node in get_nodes():
                servers.append( create_expandrive_server(server_address="manager.sabeti-aws.net", 
                                                         username="", 
                                                         remote_path="/srv/samba/home/miseq", 
                                                         nickname=node["hostname"],
                                                         port= int(node["port"]) ))

            print("Updating ExpanDrive")
            with open(settings_file_modified, "w") as outf:
                with open(settings_file,"r") as inf:
                    existing_server_list = json.load(inf)
                    while(len(servers)):
                        node = servers.pop()
                        match_found = False
                        for drive in existing_server_list:
                            if drive["name"] == node["name"]:
                                match_found = True
                                drive["port"] = node["port"]
                        if not match_found:
                            existing_server_list.append(node)
                    existing_server_list.extend(servers)
                    outf.write(json.dumps(existing_server_list))

            shutil.move(settings_file_modified, settings_file)

        start_process(expandrive_executable)
