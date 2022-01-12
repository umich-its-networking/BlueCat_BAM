#!/usr/bin/env python

"""
get_shared_networks.py network_ip-or-shared_name
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
    "ident", help="CIDR or IP address of the network, or the shared network name"
)
config.add_argument(
    "--group", "-g", help="shared network group name", default="Shared Networks"
)
config.add_argument(
    "--logging",
    "-l",
    help="log level, default WARNING (30), use INFO for more, "
    + "caution: level DEBUG(10) or less will show the password in the login call",
    default=os.getenv("BLUECAT_LOGGING", "WARNING"),
)
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.logging)

configuration_name = args.configuration
ident = args.ident
group = args.group

with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

    configuration_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=0,
        name=configuration_name,
        type="Configuration",
    )

    configuration_id = configuration_obj["id"]

    obj, obj_type = conn.get_obj(ident, configuration_id, "IP4Network", warn=False)
    logger.info("obj %s, type %s",obj, obj_type)
    if obj_type:
        if obj:
            obj_id = obj['id']
            shared_name = obj['properties']['sharedNetwork']
    else:
        shared_name = ident

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
    tag_obj = conn.do("getEntityByName", parentId=group_id, name=shared_name, type="Tag")
    if not tag_obj or tag_obj["id"] == 0:
        print(
            "ERROR - tag",
            shared_name,
            "in group",
            group,
            "in Configuration",
            configuration_name,
            "not found",
        )
    logger.info("tag %s",tag_obj)

    # get shared networks
    network_obj_list = conn.do(
        "getSharedNetworks",
        tagId=tag_obj["id"],
    )
    for net_obj in network_obj_list:
        #print(net_obj)
        print(net_obj['type'],net_obj['name'],net_obj['properties']['CIDR'],"shared_network",net_obj['properties']['sharedNetwork'])
