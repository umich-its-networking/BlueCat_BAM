#!/usr/bin/env python

"""
resize_dhcp_ranges_by_network.py object_ident offset size
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "resize_dhcp_ranges_by_network"
__version__ = "0.1"


def get_dhcp_ranges(networkid, conn):
    """get list of ranges"""
    logger = logging.getLogger()
    range_list = conn.get_bam_api_list(
        "getEntities",
        parentId=networkid,
        type="DHCP4Range",
    )
    logger.debug(range_list)
    return range_list


def main():
    """resize_dhcp_ranges_by_network.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Resize DHCP Range given Network, offset, and size"
    )
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

    configuration_name = args.configuration
    object_ident = args.object_ident
    rangetype = ""
    offset = int(args.offset)
    size = int(args.size)
    if size == 0:
        print("ERROR - size cannot be zero")
        return

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
            cidr = entity["properties"]["CIDR"]
            print(
                "Network: %s\t%s size %s"
                % (entity["name"], cidr, ipaddress.IPv4Network(cidr).num_addresses)
            )
            # print(entity)
            do_dhcp_ranges(entity, conn, offset, size)


def do_dhcp_ranges(entity, conn, offset, size):
    """resize dhcp ranges"""
    entityId = entity["id"]
    ranges_list = get_dhcp_ranges(entityId, conn)
    for x in ranges_list:
        start = ipaddress.ip_address(x["properties"]["start"])
        end = ipaddress.ip_address(x["properties"]["end"])
        rangesize = int(end) - int(start) + 1
        print("    previous DHCP_range: %s-%s\tsize %s" % (start, end, rangesize))

        if len(ranges_list) == 1:
            # calc new range
            cidr = entity["properties"]["CIDR"]
            netsize = ipaddress.IPv4Network(cidr).num_addresses
            if size < 0:
                rangesize = netsize + size - offset
            else:
                rangesize = size
            network_ip = ipaddress.IPv4Network(cidr).network_address
            new_start = network_ip + offset
            new_end = network_ip + offset + rangesize - 1
            newrange = str(new_start) + "-" + str(new_end)
            print("new start, end", new_start, new_end, newrange)
            result = conn.do(
                "resizeRange",
                objectId=x["id"],
                range=newrange,
                options="convertOrphanedIPAddressesTo=UNALLOCATED",
            )
            if result:
                print(result)

            # now print ranges again
            ranges_list = get_dhcp_ranges(entityId, conn)
            for y in ranges_list:
                start = ipaddress.ip_address(y["properties"]["start"])
                end = ipaddress.ip_address(y["properties"]["end"])
                rangesize = int(end) - int(start) + 1
                print("    new DHCP_range: %s-%s\tsize %s" % (start, end, rangesize))
    if not ranges_list:
        print("    DHCP_range: none")
    elif len(ranges_list) > 1:
        print("    more than one range, cannot resize")


if __name__ == "__main__":
    main()
