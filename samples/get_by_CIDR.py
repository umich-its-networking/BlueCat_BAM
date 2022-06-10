#!/usr/bin/env python

"""get_by_cidr.py CIDR"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging
import re

import bluecat_bam


def main():
    """get network or block matching CIDR"""
    config = bluecat_bam.BAM.argparsecommon("get network and/or block matching CIDR")
    config.add_argument("cidr", help="CIDR Address/prefix")
    config.add_argument(
        "--type", help="optional type: IP4Block or IP4Network, defaults to both"
    )
    args = config.parse_args()
    cidr = args.cidr
    range_type = args.type

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (cfg_id, _) = conn.get_config_and_view(args.configuration, None)
        match = re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}/\d{1,2}", cidr)
        if not match:
            print("cidr not found in", cidr)
            return
        ip, prefix = cidr.split("/")
        obj = conn.do(
            "getIPRangedByIP",
            method="get",
            containerId=cfg_id,
            address=ip,
            type=range_type,
        )
        logging.info("getIPRangedByIP obj = %s", json.dumps(obj))
        if not obj or obj["id"] == 0:
            print("Not found")
            return

        # bug in BlueCat - if Block and Network have the same CIDR,
        # it should return the Network, but it returns the Block.
        # So check for a matching Network.
        if not range_type and obj["type"] == "IP4Block":
            network_obj = conn.do(
                "getEntityByCIDR",
                method="get",
                cidr=cidr,
                parentId=obj["id"],
                type="IP4Network",
            )
            if network_obj["id"]:
                obj = network_obj

        while True:  # this is a "loop - until"
            # network and block have CIDR, DHCP range does not
            found_cidr = obj["properties"].get("CIDR")
            if found_cidr:
                found_ip, found_prefix = found_cidr.split("/")
                if (
                    found_ip == ip
                    and found_prefix == prefix
                    and range_type in (None, obj["type"])
                ):
                    print(json.dumps(obj))
                if found_ip != ip or int(found_prefix) < int(prefix):
                    break
            # walk up the tree
            obj = conn.do("getParent", method="get", entityId=obj["id"])
            logging.info("parent obj = %s", json.dumps(obj))

        # print(json.dumps(ip_obj))


if __name__ == "__main__":
    main()
