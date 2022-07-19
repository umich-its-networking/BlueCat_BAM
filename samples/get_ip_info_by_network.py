#!/usr/bin/env python

"""
get_ip_info_by_network.py < list-of-networkIP
"""


# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging

import bluecat_bam


__progname__ = "get_ip_info_by_network"
__version__ = "0.1"


def get_bam_api_list(conn, apiname, **kwargs):
    """wrap api call with loop to handle 'start' and 'count'"""
    if not kwargs["count"]:
        kwargs["count"] = 1000
    if not kwargs["start"]:
        kwargs["start"] = 0
    count = kwargs["count"]
    replysize = count
    listall = []
    start = 0
    while replysize == count:
        kwargs["start"] = start
        listone = conn.do(apiname, **kwargs)
        replysize = len(listone)
        start += replysize
        # print(replysize)
        listall.extend(listone)
    return listall


def get_ip_info(networkid, conn, states):
    """get list of entities"""
    logger = logging.getLogger()
    # ip_list = conn.do(
    ip_list = get_bam_api_list(
        conn, "getEntities", parentId=networkid, type="IP4Address", start=0, count=1000,
    )
    logger.debug(ip_list)
    filtered_list = [
        ip for ip in ip_list if not states or ip["properties"]["state"] in states
    ]
    print("total_ip", len(ip_list), "filtered_ip", len(filtered_list), file=sys.stderr)
    return filtered_list


def main():
    """get_ip_info_by_network.py"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument(
        "--states",
        nargs="*",
        help="optional list of IP states to get, separated by spaces, "
        + "like DHCP_RESERVED"
        + " - see API manual for the API state names. "
        + "(default is to get all)",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    object_ident = args.object_ident
    rangetype = ""
    states = args.states

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        obj_list = conn.get_obj_list(conn, object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for entity in obj_list:
            entityId = entity["id"]

            filtered_list = get_ip_info(entityId, conn, states)
            # print(filtered_list)
            for ip in filtered_list:
                # format was: "address: %-15s  state: %-14s  mac: %-17s
                # leaseTime: %-21s  expiryTime: %-21s  name: %s"
                print(
                    "%-15s  %-14s  %-17s  %-21s  %-21s  %s"
                    % (
                        ip["properties"].get("address"),
                        ip["properties"].get("state"),
                        ip["properties"].get("macAddress"),
                        ip["properties"].get("leaseTime"),
                        ip["properties"].get("expiryTime"),
                        ip["name"],
                    )
                )
                # print(ip)
                logger.info(ip)


if __name__ == "__main__":
    main()
