#!/usr/bin/env python

"""get_serverInterfaceId.py BDDSservername --view view --cfg configuration"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


__progname__ = "get_serverInterfaceId"
__version__ = "0.1"


def main():
    """get server interface id"""
    config = argparse.ArgumentParser(
        description="BlueCat Address Manager get_serverInterfaceId"
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
    config.add_argument("bdds", help="BDDS server name")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    bdds = args.bdds

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=args.configuration,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        server_obj_list = conn.do(
            "getEntitiesByName",
            method="get",
            parentId=configuration_id,
            name=bdds,
            type="Server",
            start=0,
            count=1000,
        )
        # print("server_obj_list",json.dumps(server_obj_list))
        if len(server_obj_list) > 1:
            print("ERROR - more than one server found", json.dumps(server_obj_list))
            sys.exit(2)
        server_id = server_obj_list[0]["id"]
        if server_id == 0:
            print("ERROR - server not found")
            sys.exit(1)

        interface_obj_list = conn.do(
            "getEntities",
            method="get",
            parentId=server_id,
            type="NetworkServerInterface",
            start=0,
            count=1000,
        )
        if len(interface_obj_list) > 1:
            print(
                "ERROR - more than one interface found", json.dumps(interface_obj_list)
            )
            sys.exit(3)
        interfaceid = interface_obj_list[0]["id"]
        if interfaceid == 0:
            print("ERROR - interface not found")
            sys.exit(4)

        print(interfaceid)


if __name__ == "__main__":
    main()
