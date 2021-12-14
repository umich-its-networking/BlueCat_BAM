#!/usr/bin/env python

"""delete_ip_address.py ip-address
requires deleting linked hostnames
DHCP free will be deleted silently
future:
DHCP Reserved will be deleted with --force
DHCP active will be deleted with --force
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(
    description="delete ip address, including linked hostnames"
)
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
config.add_argument(
    "--force", "-f", help="delete active and DHCP Reserved also", action="store_true"
)
config.add_argument(
    "--states",
    help="list of IP states to delete, like --states DHCP_FREE,DHCP_ALLOCATED,DHCP_RESERVED,STATIC"
    + " (default=all)",
)
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.logging)

configuration_name = args.configuration
ip = args.ip
force = args.force
states = args.states

conn = bluecat_bam.BAM(args.server, args.username, args.password)

configuration_obj = conn.do(
    "getEntityByName",
    method="get",
    parentId=0,
    name=configuration_name,
    type="Configuration",
)

configuration_id = configuration_obj["id"]

ip_obj = conn.do(
    "getIP4Address", method="get", containerId=configuration_id, address=ip
)
ip_id = ip_obj["id"]

if ip_id == 0:
    print("IP Address not found: %s" % (ip))
else:
    address = ip_obj["properties"]["address"]
    state = ip_obj["properties"]["state"]
    expire = ip_obj["properties"]["expiryTime"]
    if states and state in states:
        if state == "DHCP_ALLOCATED":
            # change to dhcp reserved with a fake mac address, then delete
            result = conn.do(
                "changeStateIP4Address",
                addressId=ip_obj["id"],
                targetState="MAKE_DHCP_RESERVED",
                macAddress="deadbeef1234",
            )
        result = conn.do(
            "deleteWithOptions",
            method="delete",
            objectId=ip_id,
            options="noServerUpdate=true|deleteOrphanedIPAddresses=true|",
        )
        """check if IP address still exists, should get id=0 if not"""
        check_ip = conn.do("getEntityById", method="get", id=ip_id)
        check_ip_id = check_ip["id"]
        if check_ip_id == 0:
            print("Deleted IP %s %s" % (address, state))
        else:
            print("ERROR - IP address failed to delete:", json.dumps(check_ip))
    else:
        print("skipped due to state, IP %s, state %s" % (address, state))
