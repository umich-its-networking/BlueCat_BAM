#!/usr/bin/env python

"""
prep_network_for_wifi_swap.py [--offset nn] [--free nn] < list-of-networkIP

In the range needed for new devices,
Replace DHCP Reserved records with DHCP Allocated, and recreate any HostRecord's
Leave any DHCP Reserved that are outside that range,
but have enough free in the range to account for them.
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "prep_network_for_wifi_swap"
__version__ = "0.1"


def get_ip_dict(conn, networkid):
    """get dict of DHCP_ALLOCATED and DHCP_RESERVED IP's in network"""
    ip_list = conn.get_ip_list(
        networkid
    )  # , states=["DHCP_ALLOCATED", "DHCP_RESERVED"])
    ip_dict = {}
    if ip_list:
        ip_dict = conn.make_ip_dict(ip_list)
    return ip_dict


def getfield(obj, fieldname):
    """get a field for printing"""
    field = obj.get(fieldname)
    if field:
        output = fieldname + ": " + field + ", "
    else:
        output = ""
    return output


def getprop(obj, fieldname):
    """get a property for printing"""
    return getfield(obj["properties"], fieldname)


def main():
    """prep_network_for_wifi_swap.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Replace DHCP Reserved records with DHCP Allocated, and recreate any HostRecord"
        + "in the range needed for new devices"
    )
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument(
        "--offset",
        help="offset of DHCP range from beginning of network (default 5)",
        default="0",  # will convert to integer
    )
    config.add_argument(
        "--free",
        default="0",  # will convert to integer
        help="number of free IP desired",
    )
    args = config.parse_args()
    offset = int(args.offset)
    free = int(args.free)

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=args.configuration,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        obj_list = conn.get_obj_list(args.object_ident, configuration_id, "")
        logger.info("obj_list: %s", obj_list)

        for network_obj in obj_list:
            prep_one_network(conn, network_obj, offset, free)


def prep_one_network(conn, network_obj, offset, free):
    """prep one network"""
    networkid = network_obj["id"]

    print("need to use offset", offset)

    # get list of ip objects and count the types
    ip_dict = get_ip_dict(conn, networkid)
    count_of = count_types(ip_dict)

    # decide on range size
    used = 0
    if count_of.get("DHCP_RESERVED"):
        used += count_of.get("DHCP_RESERVED")
    if count_of.get("DHCP_ALLOCATED"):
        used += count_of.get("DHCP_ALLOCATED")
    range_size = used + free
    print("range_size", range_size)

    # get dhcp ranges
    range_list = conn.get_dhcp_ranges(networkid)
    range_info_list = conn.make_dhcp_ranges_list(range_list)
    # print("current", range_info_list)
    print_ranges("current", range_info_list)
    if len(range_info_list) > 1:
        print("ERROR - cannot handle multiple DHCP ranges, skipping")
        return

    # decide on start of range
    # if offset is not set (0), use start of first DHCP range,
    # else default to 5
    cidr = network_obj["properties"]["CIDR"]
    network_ip = ipaddress.IPv4Network(cidr).network_address
    if offset < 1:
        if range_info_list:
            start = range_info_list[0]["start"]
        else:
            start = network_ip + 5
    else:
        start = network_ip + offset
    end = start + range_size - 1

    # expand or add or replace ranges from offset to range_end
    # for now, only allow one range
    range_obj = range_info_list[0]["range"]
    add_update_range(range_obj, conn, networkid, start, end)
    # print resulting range
    range_list = conn.get_dhcp_ranges(networkid)
    range_info_list = conn.make_dhcp_ranges_list(range_list)
    print_ranges("    new", range_info_list)

    # inside range, "convert" DHCP_RESERVED to DHCP_ALLOCATED
    # cannot convert, so delete, recreate the host records,
    # and let renew create the DHCP_ALLOCATED
    convert_dhcp_reserved_to_allocated(conn, ip_dict, start, end)


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


def count_types(ip_dict):
    """return dict of types with count"""
    count_of = {}
    ip_sorted = sorted(ip_dict.keys())
    for ip in ip_sorted:
        obj = ip_dict[ip]
        # print(obj)
        state = obj["properties"].get("state")
        if count_of.get(state):
            count_of[state] += 1
        else:
            count_of[state] = 1
    for f, v in count_of.items():
        print(f, v)
    return count_of


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


def convert_dhcp_reserved_to_allocated(conn, ip_dict, start, end):
    """convert (replace) dhcp reserved with dhcp allocated in range start to end"""
    # inside range, "convert" DHCP_RESERVED to DHCP_ALLOCATED
    # cannot convert, so delete, recreate the host records,
    # and let renew create the DHCP_ALLOCATED
    logger = logging.getLogger()
    ip = start
    while ip <= end:
        # if in dhcp range?
        obj = ip_dict.get(ip)
        if obj:
            state = obj["properties"].get("state")
            if state == "DHCP_RESERVED":
                print_ip(obj)

                # save host records to later restore
                hostrec_list = conn.do(
                    "getLinkedEntities",
                    entityId=obj["id"],
                    type="HostRecord",
                    start=0,
                    count=1000,
                )
                # get view of each record
                hostrec_view_dict = {}
                for host_obj in hostrec_list:
                    host_id = host_obj["id"]
                    logger.info("host_id %s", host_id)
                    hostrec_view_dict[host_id] = conn.getparentview(host_id)

                # delete the record
                result = conn.do("delete", objectId=obj["id"])
                if result:
                    print("result: ", result)
                # add back the host records
                create_host_records(hostrec_list, hostrec_view_dict, conn)
        ip += 1


def create_host_records(hostrec_list, hostrec_view_dict, conn):
    """(re)create host records"""
    hostname_list = []
    for host_obj in hostrec_list:
        host_id = host_obj["id"]
        view_id = hostrec_view_dict[host_id]
        result = conn.do(
            "addHostRecord",
            absoluteName=host_obj["properties"]["absoluteName"],
            addresses=host_obj["properties"]["addresses"],
            properties="",
            ttl=host_obj["properties"].get("ttl", "-1"),
            viewId=view_id,
        )
        if result:
            print("addHostRecord result", result)
        # or assignIP4Address  ??
        hostname_list.append(host_obj["properties"]["absoluteName"])
    hostname_out = " ".join(hostname_list)
    if hostname_list:
        print(hostname_out)


def print_ip(ip):
    """print ip address object"""
    name = getfield(ip, "name")
    address = getprop(ip, "address")
    mac = getprop(ip, "macAddress")
    print(address, name, mac)
    print(
        "address %s,\tname %s,\tmacAddress %s"
        % (
            ip["properties"]["address"],
            ip["name"],
            ip["properties"]["macAddress"],
        )
    )


if __name__ == "__main__":
    main()
