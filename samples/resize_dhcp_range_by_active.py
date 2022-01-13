#!/usr/bin/env python

"""
resize_dhcp_range_by_active.py network-or-filename free
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "resize_dhcp_range_by_active"
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


def get_ip_list(networkid, conn):
    """get list of IP objects"""
    logger = logging.getLogger()
    ip_list = conn.get_bam_api_list(
        "getEntities",
        parentId=networkid,
        type="IP4Address",
    )
    logger.debug(ip_list)
    return ip_list


def main():
    """resize_dhcp_range_by_active.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Resize DHCP Range to cover all DHCP_ALLOCATED and DHCP_RESERVED IP's"
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
        help="default offset of starting IP of DHCP range, "
        + "if no dhcp ranges and no active IP's are found, "
        + "at least 2 to allow for network and gateway IP's, "
        + "at least 4 if using HSRP",
    )
    config.add_argument("free", help="minimum number of free IP's in dhcp range")
    config.add_argument(
        "--checkonly",
        action="store_true",
        help="check what the new range would be," + " but do not change anything.",
    )
    config.add_argument(
        "--activeonly",
        action="store_true",
        help="start at first active, instead of first DHCP range",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    object_ident = args.object_ident
    rangetype = "IP4Network"
    free = int(args.free)
    checkonly = args.checkonly
    activeonly = args.activeonly
    offset = int(args.offset)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)

        obj_list = conn.get_obj_list(object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for network_obj in obj_list:
            cidr = network_obj["properties"]["CIDR"]
            print(
                "Network: %s\t%s size %s"
                % (network_obj["name"], cidr, ipaddress.IPv4Network(cidr).num_addresses)
            )
            # print(network_obj)
            do_dhcp_ranges(network_obj, conn, offset, free, checkonly, activeonly)


def do_dhcp_ranges(network_obj, conn, offset, free, checkonly, activeonly):
    """do dhcp ranges"""
    logger = logging.getLogger()
    networkid = network_obj["id"]
    cidr = network_obj["properties"]["CIDR"]
    netsize = ipaddress.IPv4Network(cidr).num_addresses
    network_ip = ipaddress.IPv4Network(cidr).network_address
    broadcast_ip = ipaddress.IPv4Network(cidr).broadcast_address
    logger.debug(
        "netsize: %s, network_ip: %s, broadcast_ip: %s",
        netsize,
        network_ip,
        broadcast_ip,
    )

    # set defaults
    lowest_dhcp = broadcast_ip
    highest_active = network_ip

    # get dhcp range
    if not activeonly:
        ranges_list = get_dhcp_ranges(networkid, conn)
        if len(ranges_list) > 1:
            print("ERROR - cannot handle multiple DHCP ranges, please update by hand")
            return
        if len(ranges_list) == 1:
            range_obj = ranges_list[0]
            start = ipaddress.ip_address(range_obj["properties"]["start"])
            end = ipaddress.ip_address(range_obj["properties"]["end"])
            rangesize = int(end) - int(start) + 1
            print("    previous DHCP_range: %s-%s\tsize %s" % (start, end, rangesize))
            if start < lowest_dhcp:
                lowest_dhcp = start
    logger.debug("lowest_dhcp: %s", lowest_dhcp)

    # find limits of active IP's (DHCP_ALLOCATED) (static?) (dhcp reserved?)
    # but get all IP's, for later use?
    ip_list = conn.get_ip_list(networkid, states=["DHCP_ALLOCATED", "DHCP_RESERVED"])
    ip_dict = {}
    if ip_list:
        ip_dict = conn.make_ip_dict(ip_list)
        ip_sort = sorted(ip_dict)
        lowest_active = ip_sort[0]
        highest_active = ip_sort[-1]
        active = len(ip_list)  # no, assumes all in ranges
        logger.debug(
            "lowest_active: %s, highest_active: %s", lowest_active, highest_active
        )
        if lowest_active < lowest_dhcp:
            lowest_dhcp = lowest_active

    # choose outer limits
    if lowest_dhcp == broadcast_ip:
        # no dhcp range, no active ip
        print("no dhcp ranges and no active ip")
        lowest_dhcp = network_ip + offset
    start = lowest_dhcp
    end = max(highest_active, start - 1)
    range_size = int(end) - int(start) + 1
    logger.debug("initial range %s to %s", start, end)

    # count active in range
    active = 0
    current_free = 0
    ip = start
    while ip <= end:
        if ip_dict.get(ip):
            active += 1
        else:
            current_free += 1
        ip += 1
    logger.debug("active %s, free %s", active, current_free)
    diff = free - current_free
    logger.debug(
        "desired free %s, current free %s, diff %s", free, current_free, diff
    )

    # increase range if more free are desired
    # try to increase the range at the end
    ip = end
    while diff > 0:
        ip += 1  # next IP to check
        ip_obj = ip_dict.get(ip)
        logger.debug("moving end, checking %s", str(ip))
        if ip >= broadcast_ip:
            ip -= 1
            logger.debug("hit end of network, use %s", str(ip))
            break
        if ip_obj:
            logger.debug("active %s", str(ip_obj))
            active += 1
        else:
            logger.debug("not active %s", str(ip))
            diff -= 1
    end = ip
    range_size = int(end) - int(start) + 1
    logger.debug(
        "range now %s to %s, size %s, diff %s", str(start), str(end), range_size, diff
    )

    # try to increase the range at the start
    ip = start
    while diff > 0:
        ip -= 1  # next IP to check
        ip_obj = ip_dict.get(ip)
        logger.debug("moving start back, checking %s", str(ip))
        if ip <= network_ip + 3:
            ip += 1
            logger.debug("hit start of network, use %s", str(ip))
            break
        if ip_obj:
            logger.debug("active %s", str(ip_obj))
            active += 1
        else:
            logger.debug("not active %s", str(ip))
            diff -= 1

    start = ip
    range_size = int(end) - int(start) + 1
    logger.debug(
        "new range %s to %s, size %s, diff %s", str(start), str(end), range_size, diff
    )

    # decide new range
    if end < start:
        print("no dhcp range due to no active and no free requested")
    else:
        newrange = str(start) + "-" + str(end)
        print("new start, end, active, dhcpfree", start, end, active, free)

        if not checkonly:
            result = conn.do(
                "resizeRange",
                objectId=range_obj["id"],
                range=newrange,
                options="convertOrphanedIPAddressesTo=UNALLOCATED",
            )
            if result:
                print(result)

            # now print ranges again
            ranges_list = get_dhcp_ranges(networkid, conn)
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
