#!/usr/bin/env python

"""
add_DHCP_deployment_option.py entity optionname optionvalue --properties properties
"""

# add_DHCP_deployment_option.py 8246503 vendor-encapsulated-options F1:04:8D:D5:98:4B
# {"id": 22348235, "type": "DHCPClient", "name": "vendor-encapsulated-options",
# "value": "F1:04:8D:D5:98:4B", "properties": {"inherited": "false"}}

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


__progname__ = "add_DHCP_deployment_option"
__version__ = "0.1"


def argparsecommon():
    """set up common argparse arguments for BlueCat API"""
    config = argparse.ArgumentParser(
        description="BlueCat Address Manager add_DNS_Deployment_Role_list"
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


def getserverid(server_name, configuration_id, conn):
    """get server id, given the server domainname or displayname"""
    # try by the server displayname
    interface_obj_list = conn.do(
        "searchByObjectTypes",
        keyword=server_name,
        types="NetworkServerInterface",
        start=0,
        count=2,  # error if more than one
    )
    if len(interface_obj_list) > 1:
        print(
            "ERROR - more than one server interface found",
            json.dumps(interface_obj_list),
        )
        sys.exit(3)
    interfaceid = interface_obj_list[0]["id"]
    if interfaceid != 0:
        obj = conn.do("getParent", entityId=interfaceid)
        return obj["id"]
    # server not found by domanname
    # try by the server display name
    server_obj_list = conn.do(
        "getEntitiesByName",
        parentId=configuration_id,
        name=server_name,
        type="Server",
        start=0,
        count=2,  # error if more than one
    )
    # print(json.dumps(server_obj_list))
    if len(server_obj_list) > 1:
        print(
            "ERROR - found more than one server for name",
            server_name,
            json.dumps(server_obj_list),
        )
        sys.exit(1)
    if len(server_obj_list) < 1:
        print("ERROR - server not found for", server_name)
        sys.exit(1)
    server_id = server_obj_list[0]["id"]
    if server_id == 0:
        print("ERROR - server not found for name", server_name)
        sys.exit(1)
    return server_id


def main():
    """
    add_DHCP_deployment_option.py entityId optionname optionvalue -p properties
    """
    config = argparsecommon()
    config.add_argument("entityId")
    # cannot use None as a default value
    config.add_argument("optionname")
    config.add_argument("optionvalue")
    config.add_argument(
        "--dhcpserver", help="name of DHCP server, if option only applies to one server"
    )
    config.add_argument(
        "--properties", help='other properties as a JSON dict "{name: value}"'
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    entityId = args.entityId
    optionname = args.optionname
    optionvalue = args.optionvalue
    dhcpserver = args.dhcpserver
    properties = args.properties

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        if properties:
            prop = bluecat_bam.BAM.convert_dict_in_str_to_dict(properties)
        else:
            prop = {}

        # print(prop)
        dhcpserver_id = 0
        if dhcpserver:
            dhcpserver_id = getserverid(dhcpserver, configuration_id, conn)
            prop["server"] = dhcpserver_id
        # print(prop)

        obj_id = conn.do(
            "addDHCPClientDeploymentOption",
            entityId=entityId,
            name=optionname,
            value=optionvalue,
            properties=prop,
        )

        logger.debug(obj_id)
        # obj=conn.do("getEntityById",id=obj_id)
        # print(json.dumps(obj))

        obj = conn.do(
            "getDHCPClientDeploymentOption",
            entityId=entityId,
            name=optionname,
            serverId=dhcpserver_id,
        )
        print(json.dumps(obj))


if __name__ == "__main__":
    main()
