#!/usr/bin/env python

"""get_ip_and_network.py ip-address"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import argparse
import logging

import bluecat_bam


def main():
    """get ip and network"""
    config = argparse.ArgumentParser(description="get ip object by ip address")
    config.add_argument("ip", help="IP Address")
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
        "--logging",
        "-l",
        help="log level, default WARNING (30),"
        + "caution: level DEBUG(10) or less will show the password in the login call",
        default=os.getenv("BLUECAT_LOGGING", "WARNING"),
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    view_name = args.view
    ip = args.ip

    if not (configuration_name and view_name and ip):
        config.print_help()
        sys.exit(1)

    conn = bluecat_bam.BAM(args.server, args.username, args.password)

    configuration_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=0,
        name=configuration_name,
        type="Configuration",
    )

    configuration_id = configuration_obj["id"]

    if ip == "-":
        with sys.stdin as fd:
            for line in fd:
                if line.strip() != "":
                    get_ip_and_net(line.strip(), conn, configuration_id)
    else:
        get_ip_and_net(ip, conn, configuration_id)


def get_ip_and_net(ip, conn, configuration_id):
    """get one ip"""

    ip_obj = conn.do(
        "getIP4Address", method="get", containerId=configuration_id, address=ip
    )

    # print(json.dumps(ip_obj))

    if not ip_obj or ip_obj["id"] == 0:
        print("ip not found:", ip)
        return

    network_obj = conn.do("getParent", entityId=ip_obj["id"])

    # print(json.dumps(network_obj))

    print(
        "".join(
            (
                "network %s name %s ip %s name %s state %s ",
                "macAddress %s vendorClassIdentifier %s",
            )
        )
        % (
            network_obj["properties"]["CIDR"],
            network_obj["name"],
            ip_obj["properties"]["address"],
            ip_obj["name"],
            ip_obj["properties"]["state"],
            ip_obj["properties"].get("macAddress"),
            ip_obj["properties"].get("vendorClassIdentifier"),
        )
    )


if __name__ == "__main__":
    main()
