#!/usr/bin/env python

"""
add_network.py -i network_ip [-n network_name] [--cfg configuration_name]
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="add next dhcp reserved")
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
    "--ip", "-i", "-a", "--address", help="CIDR ip address of the network"
)
config.add_argument("--name", "-n", help="Network name (optional)", default="")
config.add_argument("--vlan", help="VLAN id number (optional)", default="")
config.add_argument(
    "--loglevel",
    "-l",
    help="log level, default WARNING (30),"
    + "caution: level DEBUG(10) or less will show the password in the login call",
    default=os.getenv("BLUECAT_LOGGING", "WARNING"),
)
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.loglevel)

configuration_name = args.configuration
view_name = args.view
network_cidr = args.ip
network_name = args.name
vlan = args.vlan

if not (configuration_name and view_name and network_cidr):
    print("need configuration and view in environment or command line options")
    config.print_help()
    sys.exit(1)

try:
    (network_ip, prefix) = network_cidr.split("/", 1)
except ValueError:
    print("failed to split CIDR into IP and prefix")
    config.print_help()
    sys.exit(1)
logging.info("network_ip %s and prefix %s", network_ip, prefix)

if not (network_ip and prefix):
    print("network or prefix is empty")
    config.print_help()
    sys.exit(1)

with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

    configuration_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=0,
        name=configuration_name,
        type="Configuration",
    )

    configuration_id = configuration_obj["id"]

    # bam getIPRangedByIP containerId=21216763 type=IP4Block address=10.215.1.10
    block_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=configuration_id,
        type="IP4Block",
        address=network_ip,
    )
    block_id = block_obj["id"]

    # print("block_obj",json.dumps(block_obj))
    # print("block_id",block_id)

    # check if network exists already
    network_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=block_id,
        type="IP4Network",
        address=network_ip,
    )
    network_id = network_obj["id"]
    # print("existing network",json.dumps(network_obj)," id ",network_id)

    if network_id == 0:
        # print("does not exist, creating it")
        # bam addIP4Network blockId=21216830 CIDR=10.215.1.10/32
        network_id = conn.do(
            "addIP4Network",
            blockId=block_id,
            CIDR=network_cidr,
            properties={"vlanid": vlan, "name": network_name},
        )

        # print("new network id",network_id)
        network_obj = conn.do("getEntityById", method="get", id=network_id)
        print("new network", json.dumps(network_obj))
    else:
        # check if exact match ******
        cidr = network_obj["properties"]["CIDR"]
        # print("CIDR",cidr)
        if cidr == network_cidr:
            # existing network, update vlan and name
            # print("was",json.dumps(network_obj))
            old_name = network_obj["name"] or ""
            old_vlan = network_obj["properties"].get("vlanid") or ""
            name = network_name
            if (name and name != old_name) or (vlan and vlan != old_vlan):
                print("update existing network", json.dumps(network_obj))
                network_obj["name"] = network_name or old_name
                network_obj["properties"]["vlanid"] = vlan or old_vlan
                if network_obj["properties"].get("sharedNetwork"):
                    del network_obj["properties"]["sharedNetwork"]
                response = conn.do("update", method="put", body=network_obj)
                network_obj = conn.do("getEntityById", method="get", id=network_id)
                print(
                    "updated network (old name",
                    old_name,
                    ", old vlan",
                    old_vlan,
                    ")",
                    json.dumps(network_obj),
                )
            else:
                print("existing network", json.dumps(network_obj))
        else:
            print("ERROR - conflicting network", json.dumps(network_obj))
