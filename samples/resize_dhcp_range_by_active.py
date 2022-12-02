#!/usr/bin/env python

"""
resize_dhcp_range_by_active.py network-or-filename offset free
[--checkonly] [--activeonly]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "resize_dhcp_range_by_active"
__version__ = "0.1"


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
    logger.setLevel(args.loglevel)

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


def do_dhcp_ranges(
    network_obj, conn, offset, free, checkonly, activeonly
):  # pylint: disable=R0914
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
    start = broadcast_ip
    end = network_ip

    # get dhcp ranges (needed even if activeonly)
    range_list = conn.get_dhcp_ranges(network_obj["id"])
    range_info_list = conn.make_dhcp_ranges_list(range_list)
    print_ranges("current", range_info_list)
    if range_info_list:
        range_dict = range_info_list[0]
        range_obj = range_dict["range"]
        if not activeonly:
            start = range_dict["start"]
    else:
        range_obj = None

    if len(range_info_list) > 1:
        print("ERROR - cannot resize multiple DHCP ranges, please update by hand")
        return
    logger.info("start: %s", start)

    # find limits of active IP's (DHCP_ALLOCATED and DHCP_RESERVED)
    ip_dict = get_ip_dict(conn, networkid)
    if ip_dict:
        ip_sort = sorted(ip_dict)
        lowest_active = ip_sort[0]
        end = ip_sort[-1]  # highest active
        logger.info("lowest active: %s, highest active: %s", lowest_active, end)
        if lowest_active < start:
            start = lowest_active

    # choose outer limits
    if start == broadcast_ip:
        # no dhcp range, no active ip
        print("no dhcp ranges and no active ip")
        start = network_ip + offset
    end = max(end, start - 1)
    range_size = int(end) - int(start) + 1
    logger.info("initial range %s to %s, size %s", start, end, range_size)

    start, end, active = add_free(start, end, free, ip_dict, network_ip, broadcast_ip)

    # decide new range
    if end < start:
        print("no dhcp range due to no active and no free requested")
    else:
        rangesize = int(end) - int(start) + 1
        avail_free = rangesize - active
        print(
            "new planned start, end, size, active, dhcpfree",
            start,
            end,
            rangesize,
            active,
            avail_free,
        )

        if not checkonly:
            add_update_range(range_obj, conn, networkid, start, end)
            # print resulting range
            range_list = conn.get_dhcp_ranges(networkid)
            range_info_list = conn.make_dhcp_ranges_list(range_list)
            print_ranges("new", range_info_list)


def add_free(start, end, free, ip_dict, network_ip, broadcast_ip):
    """expand range to match desired free"""
    logger = logging.getLogger()
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
    logger.info("active in range %s, free %s", active, current_free)
    diff = free - current_free
    logger.info("desired free %s, current free %s, diff %s", free, current_free, diff)

    # increase range if more free are desired
    limit1 = network_ip + 3
    limit2 = broadcast_ip

    # try to increase the range at the end
    ip = end
    step = 1
    ip, diff, active = expand_range(ip, step, limit1, limit2, diff, active, ip_dict)
    end = ip
    range_size = int(end) - int(start) + 1
    logger.info(
        "range now %s to %s, size %s, diff %s", str(start), str(end), range_size, diff
    )

    # try to increase the range at the start
    ip = start
    step = -1
    ip, diff, active = expand_range(ip, step, limit1, limit2, diff, active, ip_dict)
    start = ip
    range_size = int(end) - int(start) + 1
    logger.info(
        "new range %s to %s, size %s, diff %s", str(start), str(end), range_size, diff
    )

    return start, end, active


def get_ip_dict(conn, networkid):
    """get dict of DHCP_ALLOCATED and DHCP_RESERVED IP's in network"""
    ip_list = conn.get_ip_list(networkid, states=["DHCP_ALLOCATED", "DHCP_RESERVED"])
    ip_dict = {}
    if ip_list:
        ip_dict = conn.make_ip_dict(ip_list)
    return ip_dict


def expand_range(ip, step, limit1, limit2, diff, active, ip_dict):
    """returns ip, diff, active"""
    logger = logging.getLogger()
    while diff > 0:
        prev = ip
        ip += step  # next IP to check
        ip_obj = ip_dict.get(ip)
        logger.info("checking %s", str(ip))
        if ip <= limit1 or ip >= limit2:
            ip = prev
            logger.info("hit limit, use %s", str(ip))
            break
        if ip_obj:
            logger.info("active %s", str(ip_obj))
            active += 1
        else:
            logger.info("not active %s", str(ip))
            diff -= 1
    return ip, diff, active


def add_update_range(range_obj, conn, networkid, start, end):
    """add or update range"""
    newrange = str(start) + "-" + str(end)
    if range_obj:
        range_id = range_obj["id"]
        result = conn.do(
            "resizeRange",
            objectId=range_id,
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
    # range_info_list [ {"start": start, "end": end, "range": dhcp_range} ...]
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
