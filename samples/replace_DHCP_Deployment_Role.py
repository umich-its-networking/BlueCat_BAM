#!/usr/bin/env python

"""
replace_DHCP_Deployment_Role.py primaryDHCPservername [failoverDHCPservername]
< list-of-IP-or-CIDR
"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging

import bluecat_bam


__progname__ = "replace_DHCP_Deployment_Role"
__version__ = "0.1"


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
    """replace DNS Deployment Role"""
    config = bluecat_bam.BAM.argparsecommon("replace DNS Deployment Role")
    config.add_argument("primaryDHCPservername")
    # cannot use None as a default value
    config.add_argument("failoverDHCPservername", default=None)

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

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

        interface = conn.getinterface(args.primaryDHCPservername, configuration_id)
        interfaceid = interface["id"]
        logger.info("interface %s", interface)
        if args.failoverDHCPservername:
            failover_obj = conn.getinterface(
                args.failoverDHCPservername, configuration_id
            )
            failover = failover_obj["id"]
            properties = "secondaryServerInterfaceId=" + str(failover) + "|"
        else:
            properties = ""

        # now work through the zones
        for cidr in sys.stdin:
            # pattern match to cidr or zone name, fwd or rev
            # set zone_name, and cidr if applicable
            cidr = cidr.strip()
            if "/" in cidr:
                network_ip = cidr.split("/")[0]
                # (network_ip, prefix) = cidr.split("/")
                # print("CIDR", cidr, "network_ip", network_ip, "prefix", prefix)
            else:
                network_ip = cidr
            # find the block or network
            entity = get_network(network_ip, configuration_id, conn)

            if not entity:
                print("network not found", cidr)
                continue
            logger.info("found entity %s", json.dumps(entity))

            # found entityId that needs DHCP roles, check for existing roles
            entityId = entity["id"]
            roles = conn.do("getDeploymentRoles", entityId=entityId)
            for role in roles:
                # print("checking role",json.dumps(role))
                if role["service"] == "DHCP":
                    print("deleting existing role", json.dumps(role))
                    conn.do("delete", objectId=role["id"])

            roleid = add_dhcp_roles(entityId, interfaceid, properties, conn)
            print("Network", cidr, "DHCP-roleid", roleid, "added")


if __name__ == "__main__":
    main()
