#!/usr/bin/env python

"""get_by_cidr.py CIDR"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging
import re

import bluecat_bam


config = argparse.ArgumentParser(
    description="get network, block, or both matching the CIDR"
)
config.add_argument("cidr", help="CIDR Address/prefix")
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
cidr = args.cidr

if not (configuration_name and view_name and cidr):
    config.print_help()
    sys.exit(1)

match = re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}/\d{1,2}", cidr)
if not match:
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
logging.info("Configuration id = %s", configuration_id)

"""
view_obj = conn.do(
    "getEntityByName",
    method="get",
    parentId=configuration_id,
    name=view_name,
    type="View",
)
view_id = view_obj["id"]
"""

id = -1
ip, prefix = cidr.split("/")
obj = conn.do(
    "getIPRangedByIP", method="get", containerId=configuration_id, address=ip, type=""
)
id = obj["id"]
logging.info("getIPRangedByIP obj = %s", json.dumps(obj))
if id == 0:
    print("Not found")
    ranged = False
else:
    ranged = True

# bug in BlueCat - if Block and Network have the same CIDR,
# it should return the Network, but it returns the Block.
# So check for a matching Network.
if ranged and obj["type"] == "IP4Block":
    network_obj = conn.do(
        "getEntityByCIDR", method="get", cidr=cidr, parentId=id, type="IP4Network"
    )
    if network_obj["id"]:
        obj = network_obj

while ranged:  # always True or always False, this is a loop - until
    # network and block have CIDR, DHCP range does not
    found_cidr = obj["properties"].get("CIDR")
    if found_cidr:
        found_ip, found_prefix = found_cidr.split("/")
        if found_ip == ip and found_prefix == prefix:
            print(json.dumps(obj))
        if found_ip != ip or int(found_prefix) < int(prefix):
            break
    # walk up the tree
    obj = conn.do("getParent", method="get", entityId=obj["id"])
    logging.info("parent obj = %s", json.dumps(obj))

# print(json.dumps(ip_obj))
