#!/usr/bin/env python

"""get_ip.py ip-address"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="get ip object by ip address")
config.add_argument("ip", help="IP Address")
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
ip = args.ip

if not (configuration_name and view_name and ip):
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

ip_obj = conn.do(
    "getIP4Address", method="get", containerId=configuration_id, address=ip
)

print(json.dumps(ip_obj))
