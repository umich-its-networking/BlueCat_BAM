#!/usr/bin/env python

"""
get_shared_networks.py network_ip-or-shared_name
"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import re
import logging

import bluecat_bam

format_items = ["input", "ip", "name", "share"]


def main():
    """get_shared_networks.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "get_shared_networks for network name or IP"
    )
    config.add_argument(
        "ident", help="CIDR or IP address of the network, or the shared network name"
    )
    config.add_argument(
        "--list",
        nargs="+",
        default=[],
        help="space separated output column list: name ip share",
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    ident = args.ident
    format_list = args.list

    for name in format_list:
        if name not in format_items:
            print("format item not valid:", name)
            print("valid items:", format_items)
            return

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(configuration_name)
        net_list = []  # for dedup
        data_list = []
        if ident == "-":
            for line in sys.stdin:
                # remove one line ending
                line = re.sub(r"(?:\r\n|\n)$", "", line, count=1)
                get_shared_net(
                    conn, line, configuration_id, configuration_name, data_list
                )
        else:
            get_shared_net(conn, ident, configuration_id, configuration_name, data_list)

        for data in data_list:
            ip = data["ip"]
            if ip not in net_list:
                if format_list:
                    print(" ".join([data[name] for name in format_list]))
                else:
                    print(
                        "IP4Network", data["name"], ip, "shared_network", data["share"]
                    )
                net_list.append(ip)


def get_shared_net(conn, ident, configuration_id, configuration_name, data_list):
    """get one shared network, add to data_list"""
    logger = logging.getLogger()
    obj, obj_type = conn.get_obj(ident, configuration_id, "IP4Network", warn=False)
    logger.info("get_shared_net obj %s, type %s", obj, obj_type)
    shared_name = None
    if obj_type:
        if obj and obj['id'] != 0:
            shared_name = obj["properties"].get("sharedNetwork")
        else:
            print("ERROR - not found:", ident, file=sys.stderr)
            return
    else:
        shared_name = ident

    if shared_name:
        tag_obj = conn.get_shared_network_tag_by_name(shared_name, configuration_id)
        logger.info("new api tag %s", tag_obj)
        if not tag_obj:
            print(
                "ERROR - tag",
                shared_name,
                "in Configuration",
                configuration_name,
                "not found",
            )
        logger.info("get_shared_net tag %s", tag_obj)

        # get shared networks
        network_obj_list = conn.do(
            "getSharedNetworks",
            tagId=tag_obj["id"],
        )
        for obj in network_obj_list:
            # print(obj)
            data = {
                "input": ident,
                "name": obj["name"],
                "ip": obj["properties"]["CIDR"],
                "share": obj["properties"]["sharedNetwork"],
            }
            data_list.append(data)
    else:
        data = {
            "input": ident,
            "name": obj["name"],
            "ip": obj["properties"]["CIDR"],
            "share": "not-shared",
        }
        data_list.append(data)


if __name__ == "__main__":
    main()
