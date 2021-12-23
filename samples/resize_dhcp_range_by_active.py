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
        "free",
        help="offset of starting IP of DHCP range, "
        + "at least 2 to allow for network and gateway IP's, "
        + "at least 4 if using HSRP",
    )
    config.add_argument(
        "--checkonly",
        action="store_true",
        help="verify that the IP and mac addresses in the import file match"
        + " the BAM, but do not change anything.",
    )
    config.add_argument(
        "--onlyactive",
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
    onlyactive = args.onlyactive

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)

        obj_list = conn.get_obj_list(conn, object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for network_obj in obj_list:
            cidr = network_obj["properties"]["CIDR"]
            print(
                "Network: %s\t%s size %s"
                % (network_obj["name"], cidr, ipaddress.IPv4Network(cidr).num_addresses)
            )
            # print(network_obj)
            do_dhcp_ranges(network_obj, conn, free, checkonly, onlyactive)


def do_dhcp_ranges(network_obj, conn, free, checkonly, onlyactive):
    """resize dhcp ranges"""
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

    # get dhcp range
    lowest_dhcp = broadcast_ip
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
    else:
        range_obj = None
    logger.info("lowest_dhcp: %s", lowest_dhcp)

    # find limits of active IP's (DHCP_ALLOCATED) (static?)
    ip_list = get_ip_list(networkid, conn)
    lowest_active = broadcast_ip
    highest_active = network_ip
    active = 0
    for ip_obj in ip_list:
        logger.warning(
            "ip %s, state %s",
            ip_obj["properties"]["address"],
            ip_obj["properties"]["state"],
        )
        # need to make dhcp reserved inclusion optional ****
        if ip_obj["properties"]["state"] in ("DHCP_ALLOCATED", "DHCP_RESERVED"):
            active += 1
            ip_address = ipaddress.ip_address(ip_obj["properties"]["address"])
            if ip_address < lowest_active:
                lowest_active = ip_address
            if ip_address > highest_active:
                highest_active = ip_address
    logger.warning(
        "lowest_active: %s, highest_active: %s", lowest_active, highest_active
    )
    logger.warning("active %s", active)

    # choose outer limits
    if onlyactive and active > 0:
        start = lowest_active
    elif range and start > lowest_active:
        start = lowest_active
    end = min(highest_active, start - 1)
    range_size = int(end) - int(start) + 1

    # add free
    desired_size = active + free
    print("desired", desired_size, "free", free)
    if desired_size > range_size:
        # try to increase the range at the end
        diff = desired_size - (active + free)
        if end + diff >= broadcast_ip:
            end = broadcast_ip - 1
        else:
            end += diff
        range_size = int(end) - int(start) + 1

        if desired_size > range_size:
            # try to increase the range at the start
            ip_dict = {
                ipaddress.ip_address(ip_obj["properties"]["address"]): ip_obj
                for ip_obj in ip_list
            }
            diff = desired_size - range_size
            ip = start - 1
            while diff > 0:
                ip_obj = ip_dict.get(ip)
                if ip_obj and ip_obj["properties"]["state"] in (
                    "STATIC",
                    "RESERVED",
                    "GATEWAY",
                ):
                    print("free IP limited to", range_size - active)
                    break
                start = ip
                range_size = int(end) - int(start) + 1
                diff = desired_size - range_size
                ip -= 1

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
