#!/usr/bin/env python

"""
delete_dhcp_ranges_by_network.py < list-of-networkIP
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "delete_dhcp_ranges_by_network"
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


def get_dhcp_ranges(networkid, conn):
    """get list of ranges"""
    logger = logging.getLogger()
    range_list = get_bam_api_list(
        conn, "getEntities", parentId=networkid, type="DHCP4Range", start=0, count=1000,
    )
    logger.debug(range_list)
    return range_list


def main():
    """delete_dhcp_ranges_by_network.py"""
    config = bluecat_bam.BAM.argparsecommon()
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
            cidr = entity["properties"]["CIDR"]
            print(
                "Network: %s\t%s size %s"
                % (entity["name"], cidr, ipaddress.IPv4Network(cidr).num_addresses)
            )
            # print(entity)
            print_dhcp_ranges(entityId, conn)


def print_dhcp_ranges(entityId, conn):
    """print dhcp ranges"""
    ranges_list = get_dhcp_ranges(entityId, conn)
    for x in ranges_list:
        start = ipaddress.ip_address(x["properties"]["start"])
        end = ipaddress.ip_address(x["properties"]["end"])
        rangesize = int(end) - int(start) + 1
        print("    DHCP_range: %s-%s\tsize %s" % (start, end, rangesize))
        result = conn.do("delete", objectId=x["id"])
        if result:
            print(result)
        else:
            print("Deleted")
    if not ranges_list:
        print("    DHCP_range: none")


if __name__ == "__main__":
    main()
