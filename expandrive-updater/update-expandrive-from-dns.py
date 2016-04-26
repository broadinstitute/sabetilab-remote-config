#!/usr/bin/python

import os,imp,sys,re,shutil
import subprocess
import json
import random
from os.path import exists
import platform

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

os_specific = {
    "osx":{
        "expandrive_settings_file_path": os.path.expanduser("~/Library/Application Support/ExpanDrive/expandrive5.favorites.js"),
        "process_name": "ExpanDrive", #possibly /Applications/ExpanDrive.app/Contents/MacOS/ExpanDrive
        "executable_path": "/Applications/ExpanDrive.app/Contents/MacOS/ExpanDrive"

    },
    "win10":{
        "expandrive_settings_file_path": os.path.join( os.path.dirname(os.path.expandvars('%APPDATA%')), "Local", "ExpanDrive", "expandrive5.favorites.js" ),
        "process_name": "ExpanDrive.exe",
        "executable_path": "C:\Program Files (x86)\ExpanDrive\ExpanDrive.exe"
    },
    "win7":{
        "expandrive_settings_file_path": os.path.join( os.path.dirname(os.path.expandvars('%APPDATA%')), "Local", "ExpanDrive", "expandrive5.favorites.js" ),
        "process_name": "ExpanDrive.exe",
        "executable_path": "C:\Program Files (x86)\ExpanDrive\ExpanDrive.exe"
    }
}

def os_specific_vals():
    system = platform.system()
    if system == "Darwin":
        return os_specific["osx"]
    elif system == "Windows":
        release = platform.release()
        if release == "10":
            return os_specific["win10"]
        elif release == "7":
            return os_specific["win7"]
        else:
            raise NotImplementedError("Support for your OS is not yet included")

def is_py2exe():
   return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze

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
    if is_py2exe():
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
        "type": "sftp",
        "protocol": "sftp",
        "name": nickname,
        "port": str(port),
        "reconnectAtLogon": False,
        #"authentication": "pageant",
        "private_key_file": None,
        "position": 2,
        #"mountpoint": "Z:",
        "id": "".join([chr(i) for i in random.sample(range(ord('a'), ord('z')+1),7)])
    }

    if platform.system() == "Windows":
        record["authentication"] = "pageant"
        record["mountpoint"] = "Z:"
    else:
        record["authentication"] = "publickey"
        record["mountpoint"] = "/Volumes/"+record["name"]

    return record


def kill_process(process_name):
    print("Killing", process_name)
    if platform.system() == "Windows":
        try:
            for proc in psutil.process_iter():
                if hasattr(proc, "name"):
                    if proc.name() == process_name:
                        proc.kill()
        except psutil.NoSuchProcess:
            raise IOError("%s process NOT found. Are you running the script with sudo?" % process_name)
            exit(1)
            pass
    elif platform.system() == "Darwin":
        # since psutil does not yield all processes on OSX unless sudoing
        # but 'ps -A' does work...
        import signal
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()

        for line in out.splitlines():
            if process_name in str(line):
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)

    

def start_process(executable):
    print("Starting", executable)
    if platform.system() == "Windows":
        subprocess.Popen([executable], creationflags=subprocess.CREATE_NEW_CONSOLE )
    else:
        subprocess.Popen([executable])

if __name__ == "__main__":
    #print(get_nodes())
    expandrive_executable = os_specific_vals()["executable_path"]
    if exists(expandrive_executable):
        print("Expandrive present")

        # kill expandrive
        kill_process(os_specific_vals()["process_name"])

        settings_file = os_specific_vals()["expandrive_settings_file_path"]
        settings_file_modified = settings_file + ".mod"

        #print(settings_file)
        if exists(settings_file):
            servers = []
            for node in get_nodes():
                servers.append( create_expandrive_server(server_address="manager.sabeti-aws.net", 
                                                         username="", 
                                                         remote_path="/srv/samba/home/miseq", 
                                                         nickname=node["hostname"]+"_live",
                                                         port= int(node["port"]) ))
                servers.append( create_expandrive_server(server_address="manager.sabeti-aws.net", 
                                                         username="", 
                                                         remote_path="/media/seqdata", 
                                                         nickname=node["hostname"]+"_archived",
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

            if platform.system() == "Darwin":
                import pwd
                import grp

                uid = pwd.getpwnam("nobody").pw_uid
                gid = grp.getgrnam("nogroup").gr_gid

                # if we are root, we can change the ownership
                if os.getuid() == 0:
                    os.chown(settings_file, uid, gid)
        else:
            raise IOError("ExpanDrive settings file not found")

        start_process(expandrive_executable)
