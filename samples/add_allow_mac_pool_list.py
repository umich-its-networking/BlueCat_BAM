#!/usr/bin/env python

"""
add_allow_mac_pool_list.py list-of-mac-pools-and-allow-or-deny
[--cfg configuration] [--view viewname]
< list-of-network-IPv4-or-CIDR
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging
import re

import bluecat_bam


__progname__ = "add_allow_mac_pool_list"
__version__ = "0.1"


def argparsecommon():
    """set up common argparse arguments for BlueCat API"""
    config = argparse.ArgumentParser(
        description="""BlueCat Address Manager add_allow_mac_pool_list
        list in format:  allow mac-pool-name
        or: deny mac-pool-name
        and feed stdin a list of Network IPs like 10.0.0.0 or 10.0.0.0/24"""
    )
    config.add_argument(
        "--server",
        "-s",
        # env_var="BLUECAT_SERVER",
        default=os.getenv("BLUECAT_SERVER"),
        help="BlueCat Address Manager hostname",
    )
    config.add_argument(
        "--username",
        "-u",
        # env_var="BLUECAT_USERNAME",
        default=os.getenv("BLUECAT_USERNAME"),
    )
    config.add_argument(
        "--password",
        "-p",
        # env_var="BLUECAT_PASSWORD",
        default=os.getenv("BLUECAT_PASSWORD"),
        help="password in environment, should not be on command line",
    )
    config.add_argument(
        "--configuration",
        "--cfg",
        help="BlueCat Configuration name",
        default=os.getenv("BLUECAT_CONFIGURATION"),
    )
    config.add_argument(
        "--view", help="BlueCat View", default=os.getenv("BLUECAT_VIEW")
    )
    config.add_argument(
        "--raw",
        "-r",
        default=os.getenv("BLUECAT_RAW"),
        help="set to true to not convert strings like 'name=value|...' "
        + "to dictionaries on output.  Will accept either format on input.",
    )
    config.add_argument(
        "--version", action="version", version=__progname__ + ".py " + __version__
    )
    config.add_argument(
        "--logging",
        "-l",
        help="log level, default WARNING (30),"
        + "caution: level DEBUG(10) or less will show the password in the login call",
        default=os.getenv("BLUECAT_LOGGING", "WARNING"),
    )
    return config


def readmacpoollist(mac_pool_list_file, conn, config_id):
    """read mac pool list file, create list of mac pool ids"""
    allow_deny_list = []
    with open(mac_pool_list_file, "r") as filehandle:
        for line in filehandle:
            (option_type, pool_name) = line.split()

            if option_type not in ["allow", "deny"]:
                raise Exception("ERROR - line must start with 'allow' or 'deny':", line)

            # get mac pool id
            mac_pool_obj = conn.do(
                "getEntityByName", parentId=config_id, name=pool_name, type="MACPool"
            )
            mac_pool_id = mac_pool_obj.get("id")
            if mac_pool_id == 0:
                raise Exception("ERROR - MAC Pool not found:", pool_name)
            # add tuple to list
            allow_deny_list.append((option_type, mac_pool_id, pool_name))

    print(json.dumps(allow_deny_list))
    return allow_deny_list


def add_mac_pools(entityId, allow_deny_list, conn, cidr):
    """found entityId that needs DNS roles, now add them"""

    # get existing DHCP service deployment options
    deploy_opt_obj_list = conn.do(
        "getDeploymentOptions",
        entityId=entityId,
        optionTypes="DHCPServiceOption",
        serverId=0,
    )
    existing_opt_obj_list = []
    for deploy_opt_obj in deploy_opt_obj_list:
        if deploy_opt_obj.get("name") in ("allow-mac-pool", "deny-mac-pool"):
            existing_opt_obj_list.append(
                (deploy_opt_obj.get("name"), deploy_opt_obj["properties"]["macPool"])
            )

    # add options if not already there
    for (option_type, mac_pool_id, mac_pool_name) in allow_deny_list:
        if (option_type, mac_pool_id) not in existing_opt_obj_list:
            try:
                opt_id = conn.do(
                    "addDHCPServiceDeploymentOption",
                    entityId=entityId,
                    name=option_type + "-mac-pool",
                    value="",
                    properties={"macPool": mac_pool_id},
                )
            except Exception as e:
                print(
                    "ERROR - failed to add MAC Pool"
                    + mac_pool_name
                    + "to network"
                    + cidr
                    + "message:"
                    + str(e)
                )
                raise

            print("added", opt_id, option_type, mac_pool_name)
        else:
            print("already had", option_type, mac_pool_name)


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


def get_network(cidr, config_id, conn):
    """find block or network for a CIDR"""
    # If both block and network match, return the block
    # bam getIPRangedByIP containerId=21216763 type=IP4Block address=10.2.1.0
    ip = cidr.split("/")[0]  # (ip,prefix) = cidr.split("/")
    block_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=config_id,
        type="IP4Block",
        address=ip,
    )
    # print("block_obj",json.dumps(block_obj))

    if block_obj["properties"]["CIDR"] == cidr:
        # print('found matching block',json.dumps(block_obj))
        entity = block_obj
    else:
        # find network
        network_obj = conn.do(
            "getIPRangedByIP",
            method="get",
            containerId=block_obj["id"],
            type="IP4Network",
            address=ip,
        )
        network_id = network_obj["id"]
        # print("existing network",json.dumps(network_obj))

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


def main():
    """add DNS Deployment Role list"""
    config = argparsecommon()
    config.add_argument(
        "mac_pool_list", help="file with 'allow (or deny) MAC-Pool-name' on each line"
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    view_name = args.view

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        config_id = configuration_obj["id"]

        view_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=config_id,
            name=view_name,
            type="View",
        )
        view_id = view_obj["id"]

        allow_deny_list = readmacpoollist(args.mac_pool_list, conn, config_id)

        # now work through the networks
        for line in sys.stdin:
            # pattern match to cidr or zone name, fwd or rev
            # set zone_name, and cidr if applicable
            line = line.strip()
            cidr = False
            if ".in-addr.arpa" in line:
                zone_name = line
                cidr = zonename2cidr(zone_name)
                print("found in-addr", line)
            elif "/" in line:
                cidr = line
                zone_name, errormsg = cidr2zonename(cidr)
                if errormsg:
                    print("ERROR - / in line, but not valid CIDR", line)
                    continue
                print("found /", line)
            if cidr:
                (ip, prefix) = cidr.split("/")
                print("CIDR", cidr, "zone", zone_name, "ip", ip, "prefix", prefix)

                # find the block or network
                entity = get_network(cidr, config_id, conn)

                if not entity:
                    print("network not found", line)
                    continue
                # print("found entity", json.dumps(entity))

            else:  # no cidr, so a zone name
                zone_name = line

                # search if zone exists
                entity = get_zone(zone_name, view_id, conn)

            if not entity:
                # spent hours debugging, hence the detailed dump
                # turned out to be a linefeed on the zone name read in
                # so added .strip() above
                print("not found", zone_name)
                continue

            # found entityId
            entityId = entity["id"]

            add_mac_pools(entityId, allow_deny_list, conn, cidr)


if __name__ == "__main__":
    main()
