#!/usr/bin/env python

"""add_DNS_Deployment_Role.py  entityId serverInterfaceId type properties"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import argparse
import logging

import bluecat_bam


__progname__ = "add_DNS_Deployment_Role"
__version__ = "0.1"


def main():
    """add DNS Deploymetn Role"""
    config = argparse.ArgumentParser(
        description="BlueCat Address Manager add_DNS_Deployment_Role"
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
    config.add_argument("entityId")
    config.add_argument("serverInterfaceId")
    config.add_argument("type")
    config.add_argument("properties")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    entityId = args.entityId
    serverInterfaceId = args.serverInterfaceId
    obj_type = args.type
    properties = args.properties

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        roleid = conn.do(
            "addDNSDeploymentRole",
            method="post",
            entityId=entityId,
            serverInterfaceId=serverInterfaceId,
            type=obj_type,
            properties=properties,
        )
        print(roleid)


if __name__ == "__main__":
    main()
