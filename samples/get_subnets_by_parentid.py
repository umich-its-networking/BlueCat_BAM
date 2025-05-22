#!/usr/bin/env python

"""get_subnets_by_parentid.py config view type domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(
    description='get subnets, outputs: CIDR shared-network id vlanid "name"'
)
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
config.add_argument("parent_id", help="Id of parent Configuration or Block")
config.add_argument(
    "--loglevel",
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

start_id = args.parent_id

if not start_id:
    config.print_help()
    sys.exit(1)

with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

    block_list = []
    network_list = []
    parent_id = start_id

    while True:
        blocks = conn.do(
            "getEntities",
            method="get",
            parentId=parent_id,
            type="IP4Block",
            start=0,
            count=1000,
        )
        if blocks:
            block_list.extend(blocks)
            # print("got blocks",json.dumps(blocks))

        networks = conn.do(
            "getEntities", parentId=parent_id, type="IP4Network", start=0, count=1000
        )
        if networks:
            network_list.extend(networks)
            # print("got networks",json.dumps(networks))

        # print('block list now',json.dumps(block_list))
        # print("network list now",json.dumps(network_list))
        if block_list:
            parent_obj = block_list.pop()
            parent_id = parent_obj.get("id")
            # print('new parent id',parent_id)
            if parent_id == 0:
                print("ERROR - block id is zero, block is", json.dumps(parent_obj))
                print("block list", json.dumps(block_list))
                sys.exit(1)
        else:
            # print('block list empty')
            break

    # print("results")
    print('CIDR shared-network id vlanid "name"')
    for network_obj in network_list:
        # print('network_obj',json.dumps(network_obj))
        print(
            network_obj["properties"].get("CIDR"),
            network_obj["properties"].get("sharedNetwork"),
            network_obj.get("id"),
            network_obj["properties"].get("vlanid"),
            '"' + str(network_obj.get("name")) + '"',
        )
