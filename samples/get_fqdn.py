#!/usr/bin/env python

"""get_fqdn.py config view type domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="get fqdn")
config.add_argument(
    "--server",
    "-s",
    # env_var="BLUECAT_SERVER",
    default=os.getenv("BLUECAT_SERVER"),
    help="BlueCat Address Manager hostname",
)
config.add_argument(
    "--username",
    "-u",
    # env_var="BLUECAT_USERNAME",
    default=os.getenv("BLUECAT_USERNAME"),
)
config.add_argument(
    "--password",
    "-p",
    # env_var="BLUECAT_PASSWORD",
    default=os.getenv("BLUECAT_PASSWORD"),
    help="password in environment, should not be on command line",
)
config.add_argument(
    "--configuration",
    "--cfg",
    help="BlueCat Configuration name",
    default=os.getenv("BLUECAT_CONFIGURATION"),
)
config.add_argument("--view", help="BlueCat View", default=os.getenv("BLUECAT_VIEW"))
config.add_argument("--type", help="DNS record type", default="HostRecord")
config.add_argument(
    "--host", "--hostname", "--fqdn", "--dns", "-d", help="DNS domain name or hostname"
)
config.add_argument(
    "--logging",
    "-l",
    help="log level, default WARNING (30),"
    + "caution: level DEBUG(10) or less will show the password in the login call",
    default=os.getenv("BLUECAT_LOGGING", "WARNING"),
)
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.logging)

configuration_name = args.configuration
view_name = args.view
record_type = args.type
domain_name = args.host

if not (configuration_name and view_name and record_type and domain_name):
    config.print_help()
    sys.exit(1)

conn = bluecat_bam.BAM(args.server, args.username, args.password)

configuration_obj = conn.do(
    "getEntityByName",
    method="get",
    parentId=0,
    name=configuration_name,
    type="Configuration",
)

configuration_id = configuration_obj["id"]

view_obj = conn.do(
    "getEntityByName",
    method="get",
    parentId=configuration_id,
    name=view_name,
    type="View",
)
view_id = view_obj["id"]

domain_label_list = domain_name.split(".")

search_domain = domain_label_list.pop()
current_domain = ""
parent_id = view_id

while True:
    zone = conn.do(
        "getEntityByName",
        method="get",
        parentId=parent_id,
        name=search_domain,
        type="Zone",
    )
    if zone.get("id") == 0:  # do not change parent_id if zero
        break
    parent_id = zone.get("id")
    current_domain = zone.get("name") + "." + current_domain
    search_domain = domain_label_list.pop()

if record_type.lower() != "zone":
    entity = conn.do(
        "getEntityByName",
        method="get",
        parentId=parent_id,
        name=search_domain,
        type=record_type,
    )

print(json.dumps(entity))

conn.logout()
