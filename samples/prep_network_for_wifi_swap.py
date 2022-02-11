#!/usr/bin/env python

"""
prep_network_for_wifi_swap.py [offset [freecount]] < list-of-networkIP
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging

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
        help="offset of DHCP range from beginning of network (typically 5)",
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
    print("current", range_info_list)

    # inside range, "convert" DHCP_RESERVED to DHCP_ALLOCATED
    # cannot convert, so delete, recreate the host records,
    # and let renew create the DHCP_ALLOCATED
    convert_dhcp_reserved_to_allocated(conn, ip_sorted, ip_dict)


def convert_dhcp_reserved_to_allocated(conn, ip_sorted, ip_dict):
    """convert (replace) dhcp reserved with dhcp allocated"""
    # inside range, "convert" DHCP_RESERVED to DHCP_ALLOCATED
    # cannot convert, so delete, recreate the host records,
    # and let renew create the DHCP_ALLOCATED
    logger = logging.getLogger()
    for ip in ip_sorted:
        # if in dhcp range?
        obj = ip_dict[ip]
        state = obj["properties"].get("state")
        if state == "DHCP_RESERVED":
            print_ip(ip)

            # save host records to later restore
            hostrec_list = conn.do(
                "getLinkedEntities",
                entityId=ip["id"],
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
            result = conn.do("delete", objectId=ip["id"])
            if result:
                print("result: ", result)
            # add back the host records
            create_host_records(hostrec_list, hostrec_view_dict, conn)


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
