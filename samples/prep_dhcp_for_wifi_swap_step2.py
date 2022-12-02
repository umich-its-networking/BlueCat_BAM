#!/usr/bin/env python

"""
prep_dhcp_for_wifi_swap_step2.py [--offset nn] [--free nn] < list-of-networkIP

Step1:
Add lease time 10 min if not already setup

Check for dhcp options, warn and skip if not set

Step2:
Print current data

Outside the range needed for new devices,
convert DHCP allocated to DHCP Reserved.

Move DHCP range

Deploy (figure out which servers to deploy)

In the range needed for new devices,
Replace DHCP Reserved records with DHCP Allocated, and recreate any HostRecord's
Leave any DHCP Reserved that are outside that range,
but have enough free in the range to account for them.

Deploy
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import ipaddress

import bluecat_bam


__progname__ = "prep_dhcp_for_wifi_swap_step2"
__version__ = "0.1"


def get_ip_dict(conn, networkid):
    """get dict of IP's in network"""
    ip_list = conn.get_ip_list(
        networkid
    )  # , states=["DHCP_ALLOCATED", "DHCP_RESERVED"])
    ip_dict = {}
    if ip_list:
        ip_dict = conn.make_ip_dict(ip_list)
    return ip_dict


def main():
    """prep_dhcp_for_wifi_swap_step2.py"""
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
        default="5",  # will convert to integer
        help="number of free IP desired",
    )
    args = config.parse_args()
    offset = int(args.offset)
    free = int(args.free)

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

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

        error_list = []
        for network_obj in obj_list:
            network_text = "%s\t%s\t%s" % (
                network_obj["type"],
                network_obj["name"],
                network_obj["properties"]["CIDR"],
            )
            # print(network_text)
            check_options(conn, network_obj, network_text, error_list)
            check_lease_time(conn, network_obj, network_text, error_list)
            prep_one_network(conn, network_obj, network_text, offset, free, error_list)
        if error_list:
            print("========== ERRORS ==========")
            for line in error_list:
                print(line)


def check_options(conn, network_obj, network_text, error_list):
    """verify that vendor-class-identifier and vendor-encapsulated-options are set"""
    optionlist = ["vendor-class-identifier", "vendor-encapsulated-options"]
    network_id = network_obj["id"]
    options = conn.do(
        "getDeploymentOptions",
        entityId=network_id,
        optionTypes="DHCPV4ClientOption",
        serverId=0,
    )
    found = {}
    for option in options:
        name = option.get("name")
        # print("name",name)
        if name in optionlist:
            found[name] = option["value"]
            # print("value",option['value'])
    if found.get("vendor-class-identifier") != "ArubaAP":
        errormsg = "ERROR - network %s vendor-class-identifier not set" % (network_text)
        error_list.append(errormsg)
        print(errormsg)
    if not (
        found.get("vendor-encapsulated-options")
        and len(found["vendor-encapsulated-options"]) == 11
    ):
        errormsg = "ERROR - network %s vendor-encapsulated-options not correct" % (
            network_text
        )
        error_list.append(errormsg)
        print(errormsg)


def check_lease_time(conn, network_obj, network_text, error_list):
    """check lease time 10 min"""
    logger = logging.getLogger()
    leasetime = "600"
    dhcpserver_id = 0
    errormsg = ""
    network_id = network_obj.get("id")

    for opt_name in ["default-lease-time", "max-lease-time", "min-lease-time"]:
        option = conn.do(
            "getDHCPServiceDeploymentOption",
            entityId=network_id,
            name=opt_name,
            serverId=dhcpserver_id,
        )
        logger.info(option)
        if option.get("id"):
            value = option["value"]
            if value != leasetime:
                errormsg = "ERROR - network %s option %s set to %s" % (
                    network_text,
                    opt_name,
                    value,
                )
                error_list.append(errormsg)
                print(errormsg)
        else:
            errormsg = "ERROR - network %s option %s not set" % (network_text, opt_name)
            error_list.append(errormsg)
            print(errormsg)
    if not errormsg:
        print("network %s lease time is correct" % (network_text))


def prep_one_network(conn, network_obj, network_text, offset, free, error_list):
    """prep one network"""
    networkid = network_obj["id"]

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
    if end >= ipaddress.IPv4Network(cidr).broadcast_address:
        start = network_ip + 5
        end = start + range_size - 1
        if end >= ipaddress.IPv4Network(cidr).broadcast_address:
            errormsg = "ERROR - network %s failed to create range size %s, too big" % (
                network_text,
                range_size,
            )
            error_list.append(errormsg)
            print(errormsg)
            return

    # expand or add or replace ranges from offset to range_end
    # for now, only allow one range
    if range_info_list:
        range_obj = range_info_list[0]["range"]
    else:
        range_obj = None
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
    logger = logging.getLogger()
    hostname_list = []
    for host_obj in hostrec_list:
        host_id = host_obj["id"]
        view_id = hostrec_view_dict[host_id]
        rec_id = conn.do(
            "addHostRecord",
            absoluteName=host_obj["properties"]["absoluteName"],
            addresses=host_obj["properties"]["addresses"],
            properties="",
            ttl=host_obj["properties"].get("ttl", "-1"),
            viewId=view_id,
        )
        logger.info("addHostRecord id %s", rec_id)
        # or assignIP4Address  ??
        hostname_list.append(host_obj["properties"]["absoluteName"])
    hostname_out = " ".join(hostname_list)
    if hostname_list:
        print("recreated", hostname_out)


def print_ip(ip):
    """print ip address object"""
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
