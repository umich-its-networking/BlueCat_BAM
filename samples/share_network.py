#!/usr/bin/env python

"""
share_network.py -i network_ip -n share_name [--cfg configuration_name]
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="share network")
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
config.add_argument(
    "--ip", "-i", "-a", "--address", help="CIDR ip address of the network"
)
config.add_argument("--name", "-n", help="share name", default="")
config.add_argument(
    "--group", "-g", help="shared network group name", default="Shared Networks"
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
logger.setLevel(args.loglevel)

configuration_name = args.configuration
network_cidr = args.ip
share_name = args.name
group = args.group

if not (configuration_name and share_name and network_cidr):
    print("ERROR - missing configuration, share_name, or network")
    config.print_help()
    sys.exit(1)

try:
    (network_ip, prefix) = network_cidr.split("/", 1)
except ValueError:
    print("ERROR - network_ip must include /prefix")
    config.print_help()
    sys.exit(1)
logging.info("network_ip %s and prefix %s", network_ip, prefix)

if not (network_ip and prefix):
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

    # get shared network group
    group_obj = conn.do("getEntityByName", parentId=0, type="TagGroup", name=group)
    group_id = group_obj["id"]
    if group_id == 0:
        print(
            "ERROR - shared network group",
            group,
            "in Configuration",
            configuration_name,
            "not found",
        )
        sys.exit(0)

    # get tag id
    tag_obj = conn.do("getEntityByName", parentId=group_id, name=share_name, type="Tag")
    tag_id = tag_obj["id"]
    if tag_id == 0:
        tag_id = conn.do("addTag", parentId=group_id, name=share_name, properties="")
        tag_obj = conn.do("getEntityById", id=tag_id)
        tag_id = tag_obj["id"]
    if tag_id == 0:
        print(
            "ERROR - could not find or create tag",
            share_name,
            "in group",
            group,
            "in Configuration",
            configuration_name,
            "not found",
        )
        sys.exit(0)

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
            properties={"name": share_name},
        )

        # print("new network id",network_id)
        network_obj = conn.do("getEntityById", method="get", id=network_id)
        print("new network", json.dumps(network_obj))
    else:
        # check if exact match ******
        cidr = network_obj["properties"]["CIDR"]
        # print("CIDR",cidr)
        if cidr == network_cidr:
            # existing network, update name
            # print("was",json.dumps(network_obj))
            old_name = network_obj["name"] or ""
            name = share_name
            if name and name != old_name:
                # print("update existing network", json.dumps(network_obj))
                network_obj["name"] = share_name or old_name
                # "sharedNetwork" is read-only, cannot write it
                if network_obj["properties"].get("sharedNetwork"):
                    del network_obj["properties"]["sharedNetwork"]
                response = conn.do("update", method="put", body=network_obj)
                network_obj = conn.do(
                    "getEntityById",
                    method="get",
                    id=network_id,
                )
                print(
                    "updated network (old name",
                    old_name,
                    ")",
                    json.dumps(network_obj),
                )
            # else:
            # print("existing network", json.dumps(network_obj))
        else:
            print("ERROR - conflicting network", json.dumps(network_obj))

    # check shared network
    shared = network_obj["properties"].get("sharedNetwork")
    if shared and shared != share_name:
        # remove shared network link
        print("WARN - removing shared network", shared)
        conn.do("unshareNetwork", networkId=network_id)
    if not shared or shared != share_name:
        # add new shared network link
        conn.do("shareNetwork", networkId=network_id, tagId=tag_id)
        network_obj = conn.do(
            "getEntityById",
            method="get",
            id=network_id,
        )
        if network_obj["properties"].get("sharedNetwork") != share_name:
            print(
                "ERROR - could not set network",
                network_ip,
                "to shared network",
                share_name,
            )

print(json.dumps(network_obj))
