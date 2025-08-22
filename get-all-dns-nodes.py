#!/usr/bin/env python3

import re
from datetime import datetime

import yaml # pip install PyYAML
import boto.route53 # pip install boto==2.39.0
from dateutil.parser import parse as parsedate # python-dateutil

aws_access_key_id = ""
aws_secret_access_key = ""
hosted_zone_domain_name = "example.net"
# must have trailing period
hosted_zone_domain_name = hosted_zone_domain_name + "." if hosted_zone_domain_name[-1] != "." else hosted_zone_domain_name

# IAM policy should be something like:
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

#conn = boto.route53.connect_to_region('us-west-2')


#print(records)

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
    nodes = []

    conn = boto.route53.connection.Route53Connection(aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    zone = conn.get_zone(hosted_zone_domain_name)
    records = [r for r in conn.get_all_rrsets(zone.id)]

    for rec in records:
        if rec.type == "TXT":
            txt_rec_value = rec.resource_records[0].decode("utf-8").strip('"')
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

    return nodes

if __name__ == "__main__":
    print(get_nodes())


