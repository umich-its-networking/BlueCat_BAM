#!/usr/bin/env python

"""
add_dhcp_range.py < list-of-networkIP
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress
import requests

import bluecat_bam


__progname__ = "add_dhcp_range"
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
        conn,
        "getEntities",
        parentId=networkid,
        type="DHCP4Range",
        start=0,
        count=1000,
    )
    logger.debug(range_list)
    return range_list


def main():
    """add_dhcp_range.py"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument(
        "offset",
        help="offset of starting IP of DHCP range, "
        + "at least 2 to allow for network and gateway IP's, "
        + "at least 4 if using HSRP",
    )
    config.add_argument(
        "size",
        help="size of DHCP range, or if negative, "
        + "offset from end of network (-1 fills to end, -2 leaves one unused, etc)",
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    rangetype = ""
    offset = int(args.offset)
    size = int(args.size)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=args.configuration,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        obj_list = conn.get_obj_list(args.object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for entity in obj_list:
            entityId = entity["id"]
            cidr = entity["properties"]["CIDR"]
            netsize = ipaddress.IPv4Network(cidr).num_addresses
            print("Network: %s\t%s size %s" % (entity["name"], cidr, netsize))
            # print(entity)

            if size < 0:
                rangesize = netsize + size - offset
            else:
                rangesize = size
            try:
                result = conn.do(
                    "addDHCP4RangeBySize",
                    networkId=entityId,
                    offset=offset,
                    size=rangesize,
                    properties="",
                )
                print("added dhcp range, id=", result)
            except requests.exceptions.HTTPError as e:
                print("ERROR adding dhcp range:", e)

            print_dhcp_ranges(entityId, conn)


def print_dhcp_ranges(entityId, conn):
    """print dhcp ranges"""
    ranges_list = get_dhcp_ranges(entityId, conn)
    for x in ranges_list:
        start = ipaddress.ip_address(x["properties"]["start"])
        end = ipaddress.ip_address(x["properties"]["end"])
        rangesize = int(end) - int(start) + 1
        print("    DHCP_range: %s-%s\tsize %s" % (start, end, rangesize))
    if not ranges_list:
        print("    DHCP_range: none")


if __name__ == "__main__":
    main()
