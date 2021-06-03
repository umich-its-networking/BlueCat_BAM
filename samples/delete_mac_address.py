#!/usr/bin/env python

"""delete_mac_address.py mac-address
requires deleting or unlinking IP addresses
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
    description="delete mac address, including linked DHCP reserved IP's"
)
config.add_argument("mac", help="MAC Address")
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
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.logging)

configuration_name = args.configuration
view_name = args.view
mac = args.mac
force = args.force

if not (configuration_name and view_name and mac):
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

mac_obj = conn.do(
    "getMACAddress", method="get", configurationId=configuration_id, macAddress=mac
)
mac_id = mac_obj["id"]
if mac_id == 0:
    print("MAC Address not found: %s" % (mac))
else:

    ip_obj_list = conn.do(
        "getLinkedEntities", entityId=mac_id, type="IP4Address", start=0, count=9999
    )

    print(json.dumps(mac_obj))
    print(json.dumps(ip_obj_list))
    out = mac
    for ip_obj in ip_obj_list:
        out = (
            out
            + " "
            + ip_obj["properties"]["address"]
            + " "
            + ip_obj["properties"]["expiryTime"]
        )
        state = ip_obj["properties"]["state"]
        if state == "DHCP_FREE" or (
            force and state in ("DHCP_ALLOCATED", "DHCP_RESERVED")
        ):
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
                objectId=ip_obj["id"],
                options="noServerUpdate=true|deleteOrphanedIPAddresses=true|",
            )
            """check if IP address still exists, should get id=0 if not"""
            check_ip = conn.do("getEntityById", method="get", id=ip_obj["id"])
            check_ip_id = check_ip["id"]
            if check_ip_id == 0:
                print("Deleted IP %s" % (ip_obj["properties"]["address"]))
            else:
                print("ERROR - IP address failed to delete:")
                print(json.dumps(check_ip))
        else:
            print(
                "not DHCP_FREE, IP %s, state %s"
                % (ip_obj["properties"]["address"], ip_obj["properties"]["state"])
            )
    result = conn.do("delete", method="delete", objectId=mac_obj["id"])
    """check if MAC address still exists, should get id=0 if not"""
    check_mac = conn.do("getEntityById", method="get", id=mac_obj["id"])
    check_mac_id = check_mac["id"]
    if check_mac_id == 0:
        print("Deleted MAC %s" % (mac_obj["properties"]["address"]))
    else:
        print("ERROR - MAC address failed to delete:")
        print(json.dumps(check_mac))
    print(out)
