#!/usr/bin/env python

"""
delete_deployment_options.py network|block|dhcprange
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


__progname__ = "delete_deployment_options.py"
__version__ = "0.1"


def main():
    """delete_deployment_options"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
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
        + " - see API manual for the API option names"
        + " (this argument is required)",
        required=True,
    )

    args = config.parse_args()
    object_ident = args.object_ident

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

        entity_list = conn.get_obj_list(conn, object_ident, configuration_id, args.type)
        for obj in entity_list:
            obj_id = obj.get('id')
            delete_deployment_option(conn, args, obj_id)


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


def delete_deployment_option(conn, args, obj_id):
    """delete deployment options for the range"""
    logger = logging.getLogger()
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
        if "false" in inherited:
            result = conn.do("delete", objectId=option["id"])
            if result:
                print("result: ", result)
        else:
            print("inherited option, cannot delete from here")


def get_range(conn, object_ident, configuration_id, rangetype):
    """get range - block, network, or dhcp range - by ip"""
    logger = logging.getLogger()
    logger.info("get_range: %s", object_ident)
    obj = conn.do(
        "getIPRangedByIP",
        address=object_ident,
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
