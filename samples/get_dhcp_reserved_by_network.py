#!/usr/bin/env python

"""
get_dhcp_reserved_by_network.py < list-of-networkIP
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging

import bluecat_bam


__progname__ = "get_dhcp_reserved_by_network"
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


def get_dhcp_reserved(networkid, conn, logger):
    """get list of entities"""
    # ip_list = conn.do(
    ip_list = get_bam_api_list(
        conn,
        "getEntities",
        parentId=networkid,
        type="IP4Address",
        start=0,
        count=1000,
    )
    logger.debug(ip_list)
    reserved_list = [
        ip for ip in ip_list if ip["properties"]["state"] == "DHCP_RESERVED"
    ]
    print("dhcp", len(ip_list), "reserved", len(reserved_list), file=sys.stderr)
    return reserved_list


def main():
    """get_dhcp_reserved_by_network.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Get list of all DHCP_RESERVED in a Network"
    )
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    object_ident = args.object_ident
    rangetype = ""

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        obj_list = conn.get_obj_list(object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for entity in obj_list:
            entityId = entity["id"]

            reserved_list = get_dhcp_reserved(entityId, conn, logger)
            # print(reserved_list)
            for ip in reserved_list:
                print(
                    "address: %-15s  mac: %s  name: %s"
                    % (
                        ip["properties"]["address"],
                        ip["properties"]["macAddress"],
                        ip["name"],
                    )
                )
                logger.info(ip)


if __name__ == "__main__":
    main()
