#!/usr/bin/env python

"""
count_states_by_network.py  network
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "count_states_by_network"
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


def get_ip_list(networkid, conn):
    """get list of IP objects"""
    logger = logging.getLogger()
    ip_list = get_bam_api_list(
        conn, "getEntities", parentId=networkid, type="IP4Address", start=0, count=1000,
    )
    logger.debug(ip_list)
    return ip_list


def make_ip_dict(conn, object_ident, configuration_id):
    """make ip dict"""
    logger = logging.getLogger()
    obj_list = conn.get_obj_list(conn, object_ident, configuration_id, "")
    logger.info("obj_list: %s", obj_list)
    ip_dict = {}
    for entity in obj_list:
        entityId = entity["id"]
        matching_list = get_ip_list(entityId, conn)
        for ip in matching_list:
            ip_dict[ip["properties"]["address"]] = ip
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
    """count_states_by_network.py"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "network",
        help="IP4Network (n.n.n.n/...), or entityId (all digits), "
        + "or a filename or stdin('-') with either of those on each line.",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)

        network_obj_list = conn.get_obj_list(conn, args.network, configuration_id, "")
        logger.info("network_obj_list: %s", network_obj_list)

        # {"id": 17396816, "name": "MYPC-1450", "type": "IP4Address",
        # "properties": {"address": "10.0.1.244", "state":
        # "DHCP_RESERVED", "macAddress": "DE-AD-BE-EF-16-E8"}}

        for network in network_obj_list:
            networkid = network["id"]
            ip_obj_list = get_ip_list(networkid, conn)
            ip_dict = {}
            for ip in ip_obj_list:
                ip_dict[ip["properties"]["address"]] = ip

            range_list = get_dhcp_ranges(networkid, conn)
            range_info_list = get_dhcp_ranges_info(range_list)

            # print(network)
            cidr = network["properties"]["CIDR"]
            network_net = ipaddress.IPv4Network(cidr)
            netsize = ipaddress.IPv4Network(cidr).num_addresses
            print("%s size of Network: %s\t%s" % (netsize, network["name"], cidr))
            print_dhcp_ranges(networkid, conn)

            (count_in, count_out) = count_network(network_net, range_info_list, ip_dict)
            print_counts(count_in, count_out)
            print("")


def print_counts(count_in, count_out):
    """print counts"""
    print("in ranges:")
    for state in sorted(count_in.keys()):
        count = count_in[state]
        print(count, state)
    print("outside ranges:")
    for state in sorted(count_out.keys()):
        count = count_out[state]
        print(count, state)


def count_network(network_net, range_info_list, ip_dict):
    """count states in a network"""
    # in_range=False    # future - count in each range
    i = 0
    (rangestart, rangeend) = get_info(i, range_info_list, network_net)
    count_in = {}  # in DHCP ranges
    count_out = {}  # out of DHCP ranges
    for ip in network_net.hosts():
        entity = ip_dict.get(str(ip))
        if entity:
            prop = ip_dict[str(ip)].get("properties")
            if prop:
                state = prop.get("state")
            else:
                state = "noprop"
        else:
            state = "Free"
        # check if in a DHCP range
        while ip > rangeend:
            i += 1
            (rangestart, rangeend) = get_info(i, range_info_list, network_net)
        if ip >= rangestart:  # in range
            if count_in.get(state):
                count_in[state] += 1
            else:
                count_in[state] = 1
        else:  # not in a DHCP range
            if count_out.get(state):
                count_out[state] += 1
            else:
                count_out[state] = 1
    return (count_in, count_out)


def get_info(i, range_info_list, network_net):
    """get the info on this dhcp_range"""
    if i < len(range_info_list):
        range_info = range_info_list[i]
        rangestart = range_info["start"]
        rangeend = range_info["end"]
    else:
        rangestart = network_net.broadcast_address
        rangeend = rangestart
    return (rangestart, rangeend)


def print_dhcp_ranges(networkid, conn):
    """print dhcp ranges"""
    ranges_list = get_dhcp_ranges(networkid, conn)
    for x in ranges_list:
        start = ipaddress.ip_address(x["properties"]["start"])
        end = ipaddress.ip_address(x["properties"]["end"])
        rangesize = int(end) - int(start) + 1
        print("%s size of DHCP_range: %s-%s" % (rangesize, start, end))
    if not ranges_list:
        print("    DHCP_range: none")


def get_dhcp_ranges_info(range_list):
    """return sorted list of dict with the start and end IP ipaddress objects
    and the range object, like:
    [
        { "start": start_ip_obj, "end": end_ip_obj, "range": range_obj }
        ...
    ]"""
    logger = logging.getLogger()
    range_info_list = []
    for dhcp_range in range_list:
        start = ipaddress.ip_address(dhcp_range["properties"]["start"])
        end = ipaddress.ip_address(dhcp_range["properties"]["end"])
        range_info_list.append({"start": start, "end": end, "range": dhcp_range})
    logger.info(range_info_list)
    range_info_list.sort(key=lambda self: self["start"])
    return range_info_list


def get_dhcp_ranges(networkid, conn):
    """get list of ranges"""
    logger = logging.getLogger()
    range_list = get_bam_api_list(
        conn, "getEntities", parentId=networkid, type="DHCP4Range", start=0, count=1000,
    )
    logger.debug(range_list)
    return range_list


if __name__ == "__main__":
    main()
