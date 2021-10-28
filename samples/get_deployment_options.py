#!/usr/bin/env python

"""
get_deployment_options.py network|block|dhcprange
[--cfg configuration]

Use any IP Address in the range, the closest range will be used.
For the specified network, block, or dhcprange,
list their deployment options
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import json
import argparse
import logging

import bluecat_bam


__progname__ = "get_deployment_options.py"
__version__ = "0.1"


def argparsecommon():
    """set up common argparse arguments for BlueCat API"""
    config = argparse.ArgumentParser(
        description="BlueCat Address Manager " + __progname__
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
    config.add_argument(
        "--view", help="BlueCat View", default=os.getenv("BLUECAT_VIEW")
    )
    config.add_argument(
        "--raw",
        "-r",
        default=os.getenv("BLUECAT_RAW"),
        help="set to true to not convert strings like 'name=value|...' "
        + "to dictionaries on output.  Will accept either format on input.",
    )
    config.add_argument(
        "--version", action="version", version=__progname__ + ".py " + __version__
    )
    config.add_argument(
        "--logging",
        "-l",
        help="log level, default WARNING (30),"
        + "caution: level DEBUG(10) or less will show the password in the login call",
        default=os.getenv("BLUECAT_LOGGING", "WARNING"),
    )
    return config


def get_network(cidr, configuration_id, conn):
    """find block or network for a CIDR"""
    # If both block and network match, return the block
    # bam getIPRangedByIP containerId=21216763 type=IP4Block address=10.2.1.0
    ip = cidr.split("/")[0]  # (ip,prefix) = cidr.split("/")
    block_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=configuration_id,
        type="IP4Block",
        address=ip,
    )
    # print("block_obj",json.dumps(block_obj))

    if block_obj["properties"]["CIDR"] == cidr:
        # print('found matching block',json.dumps(block_obj))
        entity = block_obj
    else:
        # find network
        network_obj = conn.do(
            "getIPRangedByIP",
            method="get",
            containerId=block_obj["id"],
            type="IP4Network",
            address=ip,
        )
        network_id = network_obj["id"]
        # print("existing network",json.dumps(network_obj))

        if network_id == 0:
            entity = {}
        elif network_obj["properties"]["CIDR"] == cidr:
            # print("found matching network",json.dumps(network_obj))
            entity = network_obj
        else:
            entity = {}
    return entity


def main():
    """get_deployment_options"""
    config = argparsecommon()
    config.add_argument(
        "address",
        help="Starting IP of network, block, or dhcprange"
            + ", or filename containing a list of those",
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    address = args.address

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]
        logger.info(json.dumps(configuration_obj))

        obj = conn.do(
            "getIPRangedByIP", address=address, containerId=configuration_id, type=""
        )
        # print(json.dumps(obj))
        obj_id = obj["id"]

        logging.info("getIPRangedByIP obj = %s", json.dumps(obj))
        if obj_id == 0:
            print("Not found")
            ranged = False
        else:
            ranged = True

        # bug in BlueCat - if Block and Network have the same CIDR,
        # it should return the Network, but it returns the Block.
        # So check for a matching Network.
        if ranged and obj["type"] == "IP4Block":
            cidr = obj["properties"]["CIDR"]
            network_obj = conn.do(
                "getEntityByCIDR",
                method="get",
                cidr=cidr,
                parentId=obj_id,
                type="IP4Network",
            )
            if network_obj["id"]:
                obj = network_obj
                obj_id = obj["id"]
        print(json.dumps(obj))

        options = conn.do(
            "getDeploymentOptions", entityId=obj_id, optionTypes="", serverId=-1
        )
        logger.info(json.dumps(options))
        for option in options:
            print(json.dumps(option))


if __name__ == "__main__":
    main()
