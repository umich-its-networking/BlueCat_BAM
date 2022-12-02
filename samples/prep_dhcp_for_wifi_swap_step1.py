#!/usr/bin/env python

"""
prep_dhcp_for_wifi_swap_step1.py < list-of-networkIP

Step1:
Add lease time 10 min if not already setup

Check for dhcp options, warn if not set

Step2:
Save current data to files

In the range needed for new devices,
Replace DHCP Reserved records with DHCP Allocated, and recreate any HostRecord's
Leave any DHCP Reserved that are outside that range,
but have enough free in the range to account for them.
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging

import bluecat_bam


__progname__ = "prep_dhcp_for_wifi_swap_step1"
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
    """prep_dhcp_for_wifi_swap_step1.py"""
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

    args = config.parse_args()

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
            add_lease_time(conn, network_obj, network_text, error_list)
            ip_dict = get_ip_dict(conn, network_obj["id"])
            count_types(ip_dict)
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


def add_lease_time(conn, network_obj, network_text, error_list):
    """add lease time 10 min if not already set"""
    logger = logging.getLogger()
    prop = {}
    leasetime = "600"
    dhcpserver_id = 0
    errormsg = ""
    set_lease_time = False
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
                errormsg = "ERROR - network %s option %s already set to %s" % (
                    network_text,
                    opt_name,
                    value,
                )
                error_list.append(errormsg)
                print(errormsg)
        else:
            option_id = conn.do(
                "addDHCPServiceDeploymentOption",
                entityId=network_id,
                name=opt_name,
                value=leasetime,
                properties=prop,
            )
            logger.info(option_id)
            set_lease_time = True

            option = conn.do(
                "getDHCPServiceDeploymentOption",
                entityId=network_id,
                name=opt_name,
                serverId=dhcpserver_id,
            )
            if option["value"] != leasetime:
                errormsg = "ERROR - network %s failed to set lease time, got %s" % (
                    network_text,
                    option["value"],
                )
                error_list.append(errormsg)
    if not errormsg:
        if set_lease_time:
            print("network %s set lease time" % (network_text))
        else:
            print("network %s lease time is correct" % (network_text))


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


if __name__ == "__main__":
    main()
