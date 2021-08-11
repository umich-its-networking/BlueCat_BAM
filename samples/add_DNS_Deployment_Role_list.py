#!/usr/bin/env python

"""
add_DNS_Deployment_Role_list.py list-of-DNSservername-and-role
[--cfg configuration] [--view viewname] serverlist
< list-of-CIDR-or-zonename

"serverlist"="file with servername and DNS role on each line"
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


__progname__ = "add_DNS_Deployment_Role_list"
__version__ = "0.1"


def argparsecommon():
    """set up common argparse arguments for BlueCat API"""
    config = argparse.ArgumentParser(
        description="BlueCat Address Manager add_DNS_Deployment_Role_list"
        + " - feed list of CIDR or zonename to stdin"
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


def readserverlist(serverlistfile, conn, configuration_id):
    """read server list file, create interfaces table"""
    interface_list = []
    role_validation = {  # define a set
        "NONE",
        "MASTER",
        "MASTER_HIDDEN",
        "SLAVE",
        "SLAVE_STEALTH",
        "FORWARDER",
        "STUB",
        "RECURSION",
        "AD_MASTER",
    }
    with open(serverlistfile, "r") as filehandle:

        for line in filehandle:
            (server_name, role) = line.split()

            if role not in role_validation:
                print("ERROR - role not valid:", role)
                sys.exit(1)

            server_obj_list = conn.do(
                "getEntitiesByName",
                parentId=configuration_id,
                name=server_name,
                type="Server",
                start=0,
                count=2,  # error if more than one
            )
            # print(json.dumps(server_obj_list))
            if len(server_obj_list) > 1:
                print(
                    "ERROR - found more than one server for name",
                    server_name,
                    json.dumps(server_obj_list),
                )
                sys.exit(1)
            if len(server_obj_list) < 1:
                print("ERROR - server not found for", server_name)
                sys.exit(1)
            server_id = server_obj_list[0]["id"]
            if server_id == 0:
                print("ERROR - server not found for name", server_name)
                sys.exit(1)

            interface_obj_list = conn.do(
                "getEntities",
                method="get",
                parentId=server_id,
                type="NetworkServerInterface",
                start=0,
                count=1000,
            )
            if len(interface_obj_list) > 1:
                print(
                    "ERROR - more than one interface found",
                    json.dumps(interface_obj_list),
                )
                sys.exit(3)
            interfaceid = interface_obj_list[0]["id"]
            if interfaceid == 0:
                print("ERROR - interface not found")
                sys.exit(4)

            row = (interfaceid, role, server_name)
            interface_list.append(row)

            # print(interface_obj_list[0])
            # done building the interfaces list

        # print list of interfaces and roles
        for row in interface_list:
            (interfaceid, role, server_name) = row
            # print(interfaceid, role)
    return interface_list


def add_dns_roles(entityId, zone_name, interface_list, view_id, conn):
    """found entityId that needs DNS roles, now add them"""
    print("add interfaces to zone", zone_name)
    properties = "view=" + str(view_id) + "|"
    for (interfaceid, role, server_name) in interface_list:
        role_obj = conn.do(
            "getDNSDeploymentRole",
            entityId=entityId,
            serverInterfaceId=interfaceid,
        )
        if role_obj["id"] == 0:
            roleid = conn.do(
                "addDNSDeploymentRole",
                method="post",
                entityId=entityId,
                serverInterfaceId=interfaceid,
                type=role,
                properties=properties,
            )
            print(zone_name, role, server_name, roleid)
        else:
            if role_obj["type"] == role:
                print(zone_name, role, server_name, "role exists")
            else:
                print(
                    zone_name,
                    role,
                    server_name,
                    "existing role is ",
                    role_obj["type"],
                )


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
    """find block or network for a CIDR"""
    # If both block and network match, return the block
    # bam getIPRangedByIP containerId=21216763 type=IP4Block address=10.2.1.0
    ip = cidr.split("/")[0]  # (ip,prefix) = cidr.split("/")
    block_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=configuration_id,
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
        "serverlist", help="file with servername and DNS role on each line"
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
        configuration_id = configuration_obj["id"]

        view_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=configuration_id,
            name=view_name,
            type="View",
        )
        view_id = view_obj["id"]

        interface_list = readserverlist(args.serverlist, conn, configuration_id)

        # now work through the zones
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
                entity = get_network(cidr, configuration_id, conn)

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

            # found entityId that needs DNS roles, now add them
            entityId = entity["id"]
            add_dns_roles(entityId, zone_name, interface_list, view_id, conn)


if __name__ == "__main__":
    main()
