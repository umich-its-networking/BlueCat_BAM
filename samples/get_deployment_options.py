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
        "entityId",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename with any of those on each line"
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument(
        "--type",
        help='limit to a specific type: "IP4Block", "IP4Network", or "DHCP4Range"',
        default="",
    )
    config.add_argument(
        "--options",
        nargs="*",
        help="list of options to show, separated by spaces, "
        + "like vendor-class-identifier"
        + " - see API manual for the API option names",
    )

    args = config.parse_args()
    entityId = args.entityId

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    rangetype = args.type

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

        id_list = get_id_list(conn, entityId, configuration_id, rangetype, logger)

        for obj_id in id_list:
            get_deployment_option(conn, args, obj_id, logger)


def get_id(conn, object_ident, configuration_id, rangetype, logger):
    """get id for a particular object"""
    id_pattern = re.compile(r"\d+$")
    id_match = id_pattern.match(object_ident)
    logger.info("id Match result: %s", id_match)
    if id_match:  # an id
        obj_id = object_ident
    else:  # not an id
        ip_pattern = re.compile(r"((?:\d{1,3}\.){3}\d{1,3})($|[^\d])")
        ip_match = ip_pattern.match(object_ident)
        logger.info("IP Match result: '%s'", ip_match)
        if ip_match:  # an IP
            logger.info("IP Match: '%s' and '%s'", ip_match.group(1), ip_match.group(2))
            object_ident = ip_match.group(1)
            if not rangetype:
                if ip_match.group(2) == "":
                    rangetype = "IP4Address"
                elif ip_match.group(2) == "-":
                    rangetype = "DHCP4Range"
                # "/" matches either IP4Block or IP4Network
            if rangetype == "IP4Address":
                obj = conn.do(
                    "getIP4Address",
                    method="get",
                    containerId=configuration_id,
                    address=object_ident,
                )
            else:
                obj = get_range(conn, object_ident, configuration_id, rangetype, logger)
            obj_id = obj.get("id")
        else:  # not and IP or id
            obj_id = None
    logger.info("get_id returns %s of type %s", obj, rangetype)
    return obj_id


def get_id_list(conn, object_ident, configuration_id, rangetype, logger):
    """get object, or a list of objects from a file"""
    obj_id = get_id(conn, object_ident, configuration_id, rangetype, logger)
    if obj_id:
        id_list = [obj_id]
    else:  # not an IP or id, must be a file name
        with open(object_ident) as f:
            id_list = [
                get_id(conn, line.strip(), configuration_id, rangetype, logger)
                for line in f
                if line.strip() != ""
            ]
    return id_list


def getfield(obj, fieldname):
    """get a field for printing"""
    field = obj.get(fieldname)
    if field:
        output = fieldname + ": " + field + ", "
    else:
        output = ""
    return output


def getprop(obj, fieldname):
    """get a property for printing"""
    return getfield(obj["properties"], fieldname)


def get_deployment_option(conn, args, obj_id, logger):
    """get deployment options for the range"""
    optionlist = args.options

    obj = conn.do("getEntityById", id=obj_id)
    objtype = getfield(obj, "type")
    name = getfield(obj, "name")
    cidr = getprop(obj, "CIDR")
    start = getprop(obj, "start")
    end = getprop(obj, "end")
    print("For entity: ", objtype, name, cidr, start, end)
    # print(obj)

    print("    Options:")
    options = conn.do(
        "getDeploymentOptions", entityId=obj_id, optionTypes="", serverId=-1
    )
    logger.info(json.dumps(options))
    for option in options:
        if optionlist and option.get("name") not in optionlist:
            continue
        objtype = getfield(option, "type")
        name = getfield(option, "name")
        value = getfield(option, "value")
        inherited = getprop(option, "inherited")
        print("    ", objtype, name, value, inherited)
        # print(json.dumps(option))


def get_range(conn, entityId, configuration_id, rangetype, logger):
    """get range - block, network, or dhcp range - by ip"""
    logger.info("get_range: %s", entityId)
    obj = conn.do(
        "getIPRangedByIP",
        address=entityId,
        containerId=configuration_id,
        type=rangetype,
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
        if rangetype == "" and obj["type"] == "IP4Block":
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
