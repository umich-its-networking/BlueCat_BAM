#!/usr/bin/env python

"""list_mac_pool.py pool-name-or-id"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging
import bluecat_bam


__progname__ = "list_mac_pool"
__version__ = "0.1"


def main():
    """list_mac_pool"""
    config = bluecat_bam.BAM.argparsecommon("list_mac_pool")
    config.add_argument("pool", help="MAC Pool name or id")
    config.add_argument("--ip", action="store_true", help="get associated IP Addresses")
    args = config.parse_args()

    pool = args.pool
    ip_flag = args.ip

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration, args.view)

        # get pool
        obj_type, _, _ = conn.match_type(pool)
        if obj_type == "id":
            pool_obj = conn.do("getEntityById", id=pool)
        else:
            pool_obj = conn.do(
                "getEntityByName", name=pool, parentId=configuration_id, type="MACPool"
            )
        if pool_obj and pool_obj.get("id"):
            pool_id = pool_obj["id"]
        else:
            print("ERROR - pool not found:", pool)
            return

        # get all macs in the pool
        mac_objs = conn.get_bam_api_list(
            "getLinkedEntities",
            entityId=pool_id,
            type="MACAddress",
        )
        for mac_obj in mac_objs:
            print(json.dumps(mac_obj))
            if ip_flag:
                ip_objs = conn.get_bam_api_list(
                    "getLinkedEntities", entityId=mac_obj["id"], type="IP4Address"
                )
                for ip_obj in ip_objs:
                    print("    ", json.dumps(ip_obj))


if __name__ == "__main__":
    main()
