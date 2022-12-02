#!/usr/bin/env python

"""remove_mac_from_pool.py mac-address pool-name-or-id"""

# to be python2/3 compatible:
from __future__ import print_function

import logging
import bluecat_bam


__progname__ = "remove_mac_from_pool"
__version__ = "0.1"


def main():
    """remove_mac_from_pool"""
    config = bluecat_bam.BAM.argparsecommon("remove_mac_from_pool")
    config.add_argument(
        "mac",
        help="MAC Address or id or filename",
    )
    config.add_argument("pool", help="MAC Pool name or id")
    args = config.parse_args()

    mac = args.mac
    pool = args.pool
    record_type = None

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (configuration_id, _) = conn.get_config_and_view(args.configuration, args.view)

        obj_type, _, _ = conn.match_type(pool)
        if obj_type == "id":
            pool_obj = conn.do("getEntityById", id=pool)
        else:
            pool_obj = conn.do(
                "getEntityByName", name=pool, parentId=configuration_id, type="MACPool"
            )
        if pool_obj and pool_obj.get("id"):
            pool_id = pool_obj["id"]
            pool_name = pool_obj["name"]
        else:
            print("ERROR - pool not found:", pool)
            return

        obj_list = conn.get_obj_list(mac, configuration_id, record_type)

        for mac_obj in obj_list:
            mac_id = mac_obj["id"]
            old_pool = mac_obj["properties"].get("macPool")
            if old_pool != pool_name:
                print("ERROR - MAC Address not in pool:", pool)
            new_mac_obj = remove_mac_from_pool(mac_id, pool_id, conn)
            print(new_mac_obj)


def remove_mac_from_pool(mac_id, pool_id, conn):
    """remove mac from pool, return new mac obj"""
    result = conn.do("unlinkEntities", entity1Id=mac_id, entity2Id=pool_id)
    if result:
        print("ERROR, unlink got:", result)
    new_mac_obj = conn.do("getEntityById", id=mac_id)
    return new_mac_obj


if __name__ == "__main__":
    main()
