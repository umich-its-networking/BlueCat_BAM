#!/usr/bin/env python

"""
get_shared_networks.py network_ip-or-shared_name
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import re
import argparse
import logging

import bluecat_bam

def main():
    """resize_dhcp_range_by_active.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "get_shared_networks for network name or IP"
    )
    config.add_argument(
        "ident", help="CIDR or IP address of the network, or the shared network name"
    )
    config.add_argument(
        "--group", "-g", help="shared network group name", default="Shared Networks"
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    ident = args.ident
    group = args.group

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(configuration_name)
        if ident == "-":
            for line in sys.stdin:
                # remove one line ending
                line = re.sub(r'(?:\r\n|\n)$', '', line, count=1)
                get_shared_net(conn, line, configuration_id, group )
        else:
            get_shared_net(conn, ident, configuration_id, group )


def get_shared_net(conn, ident, configuration_id, group ):
        logger = logging.getLogger()
        obj, obj_type = conn.get_obj(ident, configuration_id, "IP4Network", warn=False)
        logger.info("obj %s, type %s",obj, obj_type)
        shared_name = None
        if obj_type:
            if obj:
                obj_id = obj['id']
                shared_name = obj['properties'].get('sharedNetwork')
            else:
                print("ERROR - not found:",ident)
                return
        else:
            shared_name = ident

        if shared_name:
            # get shared network group
            group_obj = conn.do("getEntityByName", parentId=0, type="TagGroup", name=group)
            group_id = group_obj["id"]
            if group_id == 0:
                print(
                    "ERROR - shared network group",
                    group,
                    "in Configuration",
                    configuration_name,
                    "not found",
                )
                sys.exit(0)
            # get tag id
            tag_obj = conn.do("getEntityByName", parentId=group_id, name=shared_name, type="Tag")
            if not tag_obj or tag_obj["id"] == 0:
                print(
                    "ERROR - tag",
                    shared_name,
                    "in group",
                    group,
                    "in Configuration",
                    configuration_name,
                    "not found",
                )
            logger.info("tag %s",tag_obj)

            # get shared networks
            network_obj_list = conn.do(
                "getSharedNetworks",
                tagId=tag_obj["id"],
            )
            for net_obj in network_obj_list:
                #print(net_obj)
                print(net_obj['type'],net_obj['name'],net_obj['properties']['CIDR'],"shared_network",net_obj['properties']['sharedNetwork'])
        else:
            print(obj['type'],obj['name'],obj['properties']['CIDR'],"not-shared")


if __name__ == "__main__":
    main()
