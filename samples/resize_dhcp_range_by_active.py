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
    logger.info(range_list)
    return range_list


def get_ip_list(networkid, conn):
    """get list of IP objects"""
    logger = logging.getLogger()
    ip_list = conn.get_bam_api_list(
        "getEntities",
        parentId=networkid,
        type="IP4Address",
    )
    logger.info(ip_list)
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
    logger.info(
        "netsize: %s, network_ip: %s, broadcast_ip: %s",
        netsize,
        network_ip,
        broadcast_ip,
    )

    # set defaults
    new_start = broadcast_ip
    new_end = network_ip

    # get dhcp ranges
    range_list = conn.get_dhcp_ranges(network_obj["id"])
    range_info_list = conn.make_dhcp_ranges_list(range_list)
    print_ranges("current", range_info_list)

    if not activeonly:
        for r in range_info_list:
            if r["start"] < new_start:
                new_start = r["start"]
    if not range_info_list:
        # no dhcp range
        range_obj = None
    elif len(range_info_list) > 1:
        print("ERROR - cannot handle multiple DHCP ranges, please update by hand")
        return

    logger.info("new_start: %s", new_start)

    # find limits of active IP's (DHCP_ALLOCATED) (static?) (dhcp reserved?)
    # but get all IP's, for later use?
    ip_list = conn.get_ip_list(networkid, states=["DHCP_ALLOCATED", "DHCP_RESERVED"])
    ip_dict = {}
    if ip_list:
        ip_dict = conn.make_ip_dict(ip_list)
        ip_sort = sorted(ip_dict)
        lowest_active = ip_sort[0]
        new_end = ip_sort[-1]  # highest active
        active = len(ip_list)  # no, assumes all in ranges
        logger.info("lowest active: %s, highest active: %s", lowest_active, new_end)
        if lowest_active < new_start:
            new_start = lowest_active

    # choose outer limits
    if new_start == broadcast_ip:
        # no dhcp range, no active ip
        print("no dhcp ranges and no active ip")
        new_start = network_ip + offset
    start = new_start
    end = max(new_end, start - 1)
    range_size = int(end) - int(start) + 1
    logger.info("initial range %s to %s", start, end)

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
    logger.info("active %s, free %s", active, current_free)
    diff = free - current_free
    logger.info("desired free %s, current free %s, diff %s", free, current_free, diff)

    # increase range if more free are desired
    # try to increase the range at the end
    ip = end
    while diff > 0:
        ip += 1  # next IP to check
        ip_obj = ip_dict.get(ip)
        logger.info("moving end, checking %s", str(ip))
        if ip >= broadcast_ip:
            ip -= 1
            logger.info("hit end of network, use %s", str(ip))
            break
        if ip_obj:
            logger.info("active %s", str(ip_obj))
            active += 1
        else:
            logger.info("not active %s", str(ip))
            diff -= 1
    end = ip
    range_size = int(end) - int(start) + 1
    logger.info(
        "range now %s to %s, size %s, diff %s", str(start), str(end), range_size, diff
    )

    # try to increase the range at the start
    ip = start
    while diff > 0:
        ip -= 1  # next IP to check
        ip_obj = ip_dict.get(ip)
        logger.info("moving start back, checking %s", str(ip))
        if ip <= network_ip + 3:
            ip += 1
            logger.info("hit start of network, use %s", str(ip))
            break
        if ip_obj:
            logger.info("active %s", str(ip_obj))
            active += 1
        else:
            logger.info("not active %s", str(ip))
            diff -= 1

    start = ip
    range_size = int(end) - int(start) + 1
    logger.info(
        "new range %s to %s, size %s, diff %s", str(start), str(end), range_size, diff
    )

    # decide new range
    if end < start:
        print("no dhcp range due to no active and no free requested")
    else:
        print("new planned start, end, active, dhcpfree", start, end, active, free)

        if not checkonly:
            add_update_range(range_obj, conn, networkid, start, end)
            # print resulting range
            range_list = conn.get_dhcp_ranges(network_obj["id"])
            range_info_list = conn.make_dhcp_ranges_list(range_list)
            print_ranges("new", range_info_list)


def add_update_range(range_obj, conn, networkid, start, end):
    """add or update range"""
    newrange = str(start) + "-" + str(end)
    if range_obj:
        result = conn.do(
            "resizeRange",
            objectId=range_obj["id"],
            range=newrange,
            options="convertOrphanedIPAddressesTo=UNALLOCATED",
        )
        if result:
            print(result)
    else:
        range_id = conn.do(
            "addDHCP4Range",
            networkId=networkid,
            properties="",
            start=str(start),
            end=str(end),
        )
        if not range_id:
            print("ERROR adding range")


def print_ranges(msg_prefix, range_info_list):
    """print dhcp ranges"""
    ## range_info_list [ {"start": start, "end": end, "range": dhcp_range} ...]
    if range_info_list:
        for y in range_info_list:
            start = y["start"]
            end = y["end"]
            rangesize = int(end) - int(start) + 1
            print(
                "    %s DHCP_range: %s-%s\tsize %s"
                % (msg_prefix, start, end, rangesize)
            )
    else:
        print("    DHCP_range: none")


if __name__ == "__main__":
    main()
