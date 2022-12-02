#!/usr/bin/env python

"""add_access_host_and_ip.py
find fqdn HostRecord and add access right to HostRecord and it's IP to a group"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging
import requests

import bluecat_bam


config = argparse.ArgumentParser(
    description="find fqdn HostRecord and add access right to HostRecord "
    + "and it's IP to a group.  Reads list of fqdn from stdin"
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
config.add_argument("--view", help="BlueCat View", default=os.getenv("BLUECAT_VIEW"))
config.add_argument("--type", help="DNS record type", default="HostRecord")
config.add_argument("--group", help="name of group to be given Change rights")
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
logger.setLevel(args.loglevel)

configuration_name = args.configuration
view_name = args.view
record_type = args.type
group_name = args.group

# all these must be specified (or defaulted)
if not (configuration_name and view_name and record_type and group_name):
    config.print_help()
    sys.exit(1)

with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

    configuration_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=0,
        name=configuration_name,
        type="Configuration",
    )
    configuration_id = configuration_obj["id"]

    view_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=configuration_id,
        name=view_name,
        type="View",
    )
    view_id = view_obj["id"]

    group_obj = conn.do(
        "getEntityByName", method="get", parentId=0, name=group_name, type="UserGroup"
    )
    group_id = group_obj["id"]

    if not (configuration_id and view_id and group_id):
        print("error finding Configuration, View, or UserGroup")
        sys.exit(1)

    # loop over hostnames read from stdin

    # https://stackoverflow.com/questions/3670323/setting-smaller-buffer-size-for-sys-stdin
    while True:
        line = sys.stdin.readline()
        # break at end of input
        if not line:
            break

        domain_name = line.rstrip()
        # print("input: %s" % (domain_name))
        domain_label_list = domain_name.split(".")

        search_domain = domain_label_list.pop()
        current_domain = ""
        parent_id = view_id

        while True:
            zone = conn.do(
                "getEntityByName",
                method="get",
                parentId=parent_id,
                name=search_domain,
                type="Zone",
            )
            if zone.get("id") == 0:  # do not change parent_id if zero
                break
            parent_id = zone.get("id")
            current_domain = zone.get("name") + "." + current_domain
            search_domain = domain_label_list.pop()

        if record_type.lower() != "zone":
            entity = conn.do(
                "getEntityByName",
                method="get",
                parentId=parent_id,
                name=search_domain,
                type=record_type,
            )

            if entity.get("id") != 0:
                print(json.dumps(entity))
                entity_id = entity.get("id")
                logging.info("found record id: %s", entity_id)

                # get existing access right, if any
                try:
                    right = conn.do(
                        "getAccessRight", method="get", entityId=id, userId=group_id
                    )
                except requests.RequestException:
                    pass
                else:
                    logging.info("existing access to record: %s", right)

                # add access right for hostname
                right_id = conn.do(
                    "addAccessRight",
                    method="post",
                    entityId=id,
                    userId=group_id,
                    value="CHANGE",
                    overrides=None,
                    properties=None,
                )
                logging.info("added right id: %s", right_id)

                # get IP Address object id
                ips = entity["properties"]["addresses"]
                for ip in ips.split(","):
                    ip_object = conn.do(
                        "getIP4Address", containerId=configuration_id, address=ip
                    )
                    logging.info("ip object: %s", ip_object)

                    # get existing access right, if any
                    right_id = conn.do(
                        "getAccessRight", method="get", entityId=id, userId=group_id
                    )
                    logging.info("existing access to ip: %s", right_id)

                    # add access right for ip address
                    conn.do(
                        "addAccessRight",
                        method="post",
                        entityId=id,
                        userId=group_id,
                        value="CHANGE",
                        overrides=None,
                        properties=None,
                    )
                    logging.info("added right id: %s", right_id)

            else:
                print("no %s found for %s" % (record_type, domain_name))

        else:
            print("host %s zone not found" % (domain_name))
