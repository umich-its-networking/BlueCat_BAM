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
import re

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


def main():
    """get_deployment_options"""
    config = argparsecommon()
    config.add_argument(
        "address",
        help="Starting IP of network, block, or dhcprange"
            + ", or filename containing a list of those",
    )
    config.add_argument(
        "--type",
        help='limit to a specific type: "IP4Block", "IP4Network", or "DHCP4Range"',
        default=""
    )
    config.add_argument(
        "--options",
        nargs="*",
        help='list of options to show, separated by spaces, '
            + 'like vendor-class-identifier'
            + " - see API manual for the API option names"
    )

    args = config.parse_args()
    address=args.address

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    ip_pattern = re.compile("((?:\d{1,3}\.){3}\d{1,3})(?:$|[^\d])")
    match=ip_pattern.match(address)
    logger.info("Match result: %s",match)
    if match:
        address = match.group(0)
        logger.info("matched: %s",address)
        get_deployment_option(args, address, logger)
    else:
        with open(address) as f:
            for line in f:
                line=line.strip()
                logger.info("line read: %s", line)
                if line != "":  # skip blank lines
                    get_deployment_option(args, line, logger)

def get_deployment_option(args, address, logger):
    configuration_name = args.configuration
    type = args.type
    optionlist=args.options

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

        obj=get_range(conn, address, configuration_id, type, logger)
        print("IP4Block, IP4Network, or DHCP4Range found:")
        print(json.dumps(obj))
        obj_id = obj["id"]

        print("Options:")
        options = conn.do(
            "getDeploymentOptions", entityId=obj_id, optionTypes="", serverId=-1
        )
        logger.info(json.dumps(options))
        for option in options:
            if optionlist and option.get('name') not in optionlist:
                continue
            print(json.dumps(option))


def get_range(conn, address, configuration_id, type, logger):
    """get range - block, network, or dhcp range - by ip"""
    logger.info("get_range: %s", address)
    obj = conn.do(
        "getIPRangedByIP", address=address, containerId=configuration_id, type=""
    )
    # print(json.dumps(obj))
    obj_id = obj["id"]

    logging.info("getIPRangedByIP obj = %s", json.dumps(obj))
    if obj_id == 0:
        print("Not found")
        obj = None
    else:
        # bug in BlueCat - if Block and Network have the same CIDR,
        # it should return the Network, but it returns the Block.
        # So check for a matching Network.
        if type == "" and obj["type"] == "IP4Block":
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
                logger.info("IP4Network found: %s", obj)
    return obj

if __name__ == "__main__":
    main()
