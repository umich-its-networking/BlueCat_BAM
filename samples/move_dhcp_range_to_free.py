#!/usr/bin/env python

"""
move_dhcp_range_to_free.py network-or-filename size [--offset nn]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "move_dhcp_range_to_free"
__version__ = "0.1"


def main():
    """move_dhcp_range_to_free.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Move DHCP Range to free space (DHCP_FREE and unused)"
    )
    config.add_argument(
        "network_ident",
        help="Can be: IP4Network (n.n.n.n/...), network entityId (all digits), "
        + "or a filename or stdin('-') with any of those on each line ",
    )
    config.add_argument("size", help="desired size of DHCP range, ")
    config.add_argument(
        "--offset",
        help="offset of DHCP range from beginning of network (default 5)",
        default="0",  # will convert to integer
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    network_ident = args.network_ident
    rangetype = "IP4Network"
    size = int(args.size)
    offset = int(args.offset)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)

        obj_list = conn.get_obj_list(network_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for network_obj in obj_list:
            cidr = network_obj["properties"]["CIDR"]
            print(
                "Network: %s\t%s size %s"
                % (network_obj["name"], cidr, ipaddress.IPv4Network(cidr).num_addresses)
            )
            # print(network_obj)
            do_dhcp_ranges(network_obj, conn, size, offset)


def do_dhcp_ranges(network_obj, conn, size, offset):  # pylint: disable=R0914
    """do dhcp ranges"""
    logger = logging.getLogger()
    # get network info
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

    # get existing dhcp ranges
    range_list = conn.get_dhcp_ranges(network_obj["id"])
    range_info_list = conn.make_dhcp_ranges_list(range_list)
    print_ranges("current", range_info_list)
    if len(range_info_list) > 1:
        print("ERROR - cannot resize multiple DHCP ranges, please update by hand")
        return
    if range_info_list:
        range_dict = range_info_list[0]  # only one DHCP range handled
        range_obj = range_dict["range"]
    else:
        range_obj = None
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

    start, end = find_open_space(offset, network_ip, broadcast_ip, ip_dict, size)
    add_update_range(range_obj, conn, networkid, start, end)
    # print resulting range
    range_list = conn.get_dhcp_ranges(networkid)
    range_info_list = conn.make_dhcp_ranges_list(range_list)
    print_ranges("    new", range_info_list)


def find_open_space(offset, network_ip, broadcast_ip, ip_dict, size):
    """search for open space to fit range"""
    if not offset:
        offset = 5
    start = network_ip + offset
    ip = start
    mysize = 0
    while ip < broadcast_ip:
        # print("checking",ip)
        obj = ip_dict.get(ip)
        if obj:
            # print("found",obj)
            state = obj["properties"]["state"]
            if state in ("DHCP_ALLOCATED", "STATIC"):
                mysize += 1
                if mysize >= size:
                    end = ip
                    break
                # else
                ip += 1
                continue
            # else:
            ip += 1
            start = ip
            mysize = 0
            continue
        # else
        mysize += 1
        if mysize >= size:
            end = ip
            break
        ip += 1

    else:  # end of while goes here
        print("no room for range found")
        return None, None
    # break jumps to here
    # print("new range start", start, "end", end)
    return start, end


def get_ip_dict(conn, networkid):
    """get dict of DHCP_ALLOCATED and DHCP_RESERVED IP's in network"""
    ip_list = conn.get_ip_list(networkid, states=["DHCP_ALLOCATED", "DHCP_RESERVED"])
    ip_dict = {}
    if ip_list:
        ip_dict = conn.make_ip_dict(ip_list)
    return ip_dict


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
