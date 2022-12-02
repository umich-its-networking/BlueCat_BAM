#!/usr/bin/env python

"""
get_dhcp_ranges_by_network.py < list-of-networkIP
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import json
import logging
import re
import ipaddress

import bluecat_bam


__progname__ = "get_dhcp_ranges_by_network"
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


def get_dhcp_ranges(networkid, conn, logger):
    """get list of ranges"""
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


def zonename2cidr(zone_name):
    """convert zone name (...in-addr.arpa) to cidr for class A,B,C"""
    parts = zone_name.split(".")
    parts.reverse()  # updates in place
    partial = ".".join(parts[2:])
    if len(parts) == 5:
        cidr = partial + ".0/24"
    elif len(parts) == 4:
        cidr = partial + ".0.0/16"
    elif len(parts) == 3:
        cidr = partial + "0.0.0/8"
    return cidr


def cidr2zonename(cidr):
    """convert CIDR to first zone name (...in-addr.arpa)"""
    errormsg = ""
    zone_name = ""
    findip = re.match(r"[0-9]{1,3}(\.[0-9]{1,3}){3}/[0-9]{1,2}\Z", cidr)
    if findip:
        (ip, prefix) = cidr.split("/")
        octets = ip.split(".")
        if prefix <= "8":
            zone_name = octets[0] + ".in-addr.arpa"
        elif prefix <= "16":
            zone_name = octets[1] + "." + octets[0] + ".in-addr.arpa"
        elif prefix <= "24":
            zone_name = octets[2] + "." + octets[1] + "." + octets[0] + ".in-addr.arpa"
        else:
            errormsg = "not a supported CIDR"
    else:
        errormsg = "not a valid CIDR"
    return zone_name, errormsg


def get_network(cidr, configuration_id, conn):
    """find network for a CIDR"""
    # If both block and network match, return the network
    # bam getIPRangedByIP containerId=21216763 type=IP4Block address=10.2.1.0
    ip = cidr.split("/")[0]  # (ip,prefix) = cidr.split("/")
    # find network
    network_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=configuration_id,
        type="IP4Network",
        address=ip,
    )
    network_id = network_obj["id"]

    if network_id == 0:
        entity = {}
    elif network_obj["properties"]["CIDR"] == cidr:
        # print("found matching network",json.dumps(network_obj))
        entity = network_obj
    else:
        entity = {}
    return entity


def get_zone(zone_name, view_id, conn):
    """get zone object given zone name"""
    # search if zone exists
    domain_label_list = zone_name.split(".")

    search_domain = domain_label_list.pop()
    current_domain = ""
    parent_id = view_id

    while True:
        zone = conn.do(
            "getEntityByName",
            method="get",
            parentId=parent_id,
            name=search_domain,
            type="Zone",
        )
        if zone.get("id") == 0:  # do not change parent_id if zero
            break
        parent_id = zone.get("id")
        current_domain = zone.get("name") + "." + current_domain
        # print(json.dumps(domain_label_list))
        if domain_label_list:
            search_domain = domain_label_list.pop()
        else:
            search_domain = ""
            break

    if current_domain == zone_name + ".":
        # print("found zone", json.dumps(zone))
        return zone
    return {}


def get_entity_by_name_ip_cidr(conn, line, configuration_id, view_id):
    """get zone, network, or block by name or ip or cidr"""
    logger = logging.getLogger()
    cidr = False
    if ".in-addr.arpa" in line:
        zone_name = line
        cidr = zonename2cidr(zone_name)
        logger.info("found in-addr: %s", line)
    elif "/" in line:
        cidr = line
        zone_name, errormsg = cidr2zonename(cidr)
        if errormsg:
            print("ERROR - / in line, but not valid CIDR", line)
            cidr = None
        logger.info("found /: %s", line)
    if cidr:
        (ip, prefix) = cidr.split("/")
        logger.info("CIDR %s, zone %s, ip %s, prefix %s", cidr, zone_name, ip, prefix)

        # find the block or network
        entity = get_network(cidr, configuration_id, conn)

        if not entity:
            print("network not found", line)
        logger.debug("found entity %s", json.dumps(entity))

    # will not be a zone in this case, but leave the generic code here
    else:  # no cidr, so a zone name
        zone_name = line
        # search if zone exists
        entity = get_zone(zone_name, view_id, conn)
    return entity


def main():
    """get_dhcp_ranges_by_network.py"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    configuration_name = args.configuration
    object_ident = args.object_ident
    rangetype = ""

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
            entityId = entity["id"]
            cidr = entity["properties"]["CIDR"]
            print(
                "Network: %s\t%s size %s"
                % (entity["name"], cidr, ipaddress.IPv4Network(cidr).num_addresses)
            )
            # print(entity)

            # print("Ranges:")
            ranges_list = get_dhcp_ranges(entityId, conn, logger)
            # print(ranges_list)
            for x in ranges_list:
                # print(x)
                start = ipaddress.ip_address(x["properties"]["start"])
                end = ipaddress.ip_address(x["properties"]["end"])
                rangesize = int(end) - int(start) + 1
                print("    DHCP_range: %s-%s\tsize %s" % (start, end, rangesize))
            if not ranges_list:
                print("    DHCP_range: none")


if __name__ == "__main__":
    main()
