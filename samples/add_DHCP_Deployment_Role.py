#!/usr/bin/env python

"""
add_DHCP_Deployment_Role_list.py primaryDHCPservername [failoverDHCPservername]
[--cfg configuration]
< list-of-IP-or-CIDR
"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging

import bluecat_bam


__progname__ = "add_DHCP_Deployment_Role_list"
__version__ = "0.1"


def getinterfaceid(server_name, configuration_id, conn):
    """get server interface id, given the server name"""
    interface_obj_list = conn.do(
        "searchByObjectTypes",
        keyword=server_name,
        types="NetworkServerInterface",
        start=0,
        count=2,  # error if more than one
    )
    if len(interface_obj_list) > 1:
        print("ERROR - more than one interface found", json.dumps(interface_obj_list))
        sys.exit(3)
    interfaceid = interface_obj_list[0]["id"]
    if interfaceid != 0:
        return interfaceid

    # try another method, in case they gave the server display name instead
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
        print("ERROR - more than one interface found", json.dumps(interface_obj_list))
        sys.exit(3)
    interfaceid = interface_obj_list[0]["id"]
    if interfaceid == 0:
        print("ERROR - interface not found")
        sys.exit(4)
    return interfaceid


def add_dhcp_roles(entityId, interfaceid, properties, conn):
    """found entityId that needs DHCP roles, now add them"""
    role = conn.do(
        "getDHCPDeploymentRole",
        method="get",
        entityId=entityId,
        serverInterfaceId=interfaceid,
    )
    roleid = role["id"]
    if roleid != 0:
        print("role", roleid, "exists for network")
    else:
        roleid = conn.do(
            "addDHCPDeploymentRole",
            method="post",
            entityId=entityId,
            serverInterfaceId=interfaceid,
            type="MASTER",
            properties=properties,
        )
    return roleid


def get_network(network_ip, configuration_id, conn):
    """find network for an IP"""
    # bam getIPRangedByIP containerId=21216763 type=IP4Block address=10.2.1.0
    network_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=configuration_id,
        type="IP4Network",
        address=network_ip,
    )
    if network_obj["id"] == 0:
        network_obj = {}
    return network_obj


def main():
    """add DNS Deployment Role list"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument("primaryDHCPservername")
    # cannot use None as a default value
    config.add_argument("failoverDHCPservername", default="fred")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        interfaceid = getinterfaceid(args.primaryDHCPservername, configuration_id, conn)
        if args.failoverDHCPservername:
            failover = getinterfaceid(
                args.failoverDHCPservername, configuration_id, conn
            )
            properties = "secondaryServerInterfaceId=" + str(failover) + "|"
        else:
            properties = ""

        # now work through the zones
        for cidr in sys.stdin:
            # pattern match to cidr or zone name, fwd or rev
            # set zone_name, and cidr if applicable
            cidr = cidr.strip()
            if "/" in cidr:
                ip = cidr.split("/")[0]
                # (ip, prefix) = cidr.split("/")
                # print("CIDR", cidr, "ip", ip, "prefix", prefix)
            else:
                ip = cidr
            # find the block or network
            entity = get_network(ip, configuration_id, conn)

            if not entity:
                print("network not found", cidr)
                continue
            # print("found entity", json.dumps(entity))

            # found entityId that needs DNS roles, now add them
            entityId = entity["id"]
            roleid = add_dhcp_roles(entityId, interfaceid, properties, conn)
            print("Network", cidr, "DHCP-roleid", roleid)


if __name__ == "__main__":
    main()
