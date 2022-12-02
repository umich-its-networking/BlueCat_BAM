#!/usr/bin/env python

"""add_access.py
add access right for a group to an entity in BlueCat BAM"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging
import requests

import bluecat_bam


__progname__ = "add_access"
__version__ = "0.1"


def main():
    """add_access"""
    config = bluecat_bam.BAM.argparsecommon("add_access")
    config.add_argument(
        "--type",
        help="DNS record type, like HostRecord, AliasRecord, TXTRecord, "
        + "GenericRecord, etc, or Entity to get all types",
        default="Entity",
    )
    config.add_argument("entity", help="entity name, IP, CIDR, id, filename, or '-'")
    config.add_argument("--type", help="optional entity type")
    config.add_argument("group", help="name of group to be given access rights")
    config.add_argument("value", help="access right - HIDE, VIEW, ADD, CHANGE, or FULL")
    config.add_argument("--overrides")
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    record_type = args.type

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (configuration_id, view_id) = conn.get_config_and_view(
            args.configuration, args.view
        )

        obj_list = conn.get_obj_list(args.entity, view_id, record_type)

    group_obj = conn.do(
        "getEntityByName", method="get", parentId=0, name=group_name, type="UserGroup"
    )
    group_id = group_obj["id"]

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
