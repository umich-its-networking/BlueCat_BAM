#!/usr/bin/env python

"""
get_other_dns_server_roles.py
[--cfg configuration] [--view viewname]

For all DNS servers of type "other",
list their DNS roles
(then probably will delete those that have no roles)
"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging
import re

import bluecat_bam


__progname__ = "get_other_dns_server_roles.py"
__version__ = "0.1"


def getdnsservers(conn, configuration_id):
    """get list of DNS Server objects"""
    dns_server_obj_list = conn.do(
        "getEntities", count=1000, start=0, parentId=configuration_id, type="Server"
    )
    return dns_server_obj_list


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


def main():
    """get_other_dns_server_roles.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Find all DNS Deployment Roles for servers of type Other"
    )
    config.add_argument(
        "--exclude",
        "-x",
        nargs="*",
        # action="append",  # causes a list of lists
        help="server display names or hostnames to exclude, space separated",
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    configuration_name = args.configuration
    exclude_list = args.exclude
    # print(exclude_list)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        dns_server_obj_list = getdnsservers(conn, configuration_id)
        # for s in dns_server_obj_list:
        #    print(s)
        other_dns_obj_list = [
            o
            for o in dns_server_obj_list
            if o["properties"]["profile"] == "OTHER_DNS_SERVER"
        ]
        final_dns_obj_list = [
            o
            for o in other_dns_obj_list
            if o["name"] not in exclude_list
            and o["properties"]["fullHostName"] not in exclude_list
        ]

        for server in final_dns_obj_list:
            prop = server["properties"]
            roles = conn.do("getServerDeploymentRoles", serverId=server["id"])
            for role in roles:
                entity = conn.do("getEntityById", id=role["entityId"])
                # print(entity)
                if entity["type"] in ("Zone"):  # pylint: disable=C0325
                    print(
                        server["name"],
                        prop["fullHostName"],
                        prop["defaultInterfaceAddress"],
                        role["type"],
                        entity["type"],
                        entity["properties"]["absoluteName"],
                    )
                elif entity["type"] in ("EnumZone"):  # pylint: disable=C0325
                    print(
                        server["name"],
                        prop["fullHostName"],
                        prop["defaultInterfaceAddress"],
                        role["type"],
                        entity,
                    )
                elif entity["type"] in ("IP4Network", "IP4Block"):
                    if entity["properties"].get("CIDR"):
                        print(
                            server["name"],
                            prop["fullHostName"],
                            prop["defaultInterfaceAddress"],
                            role["type"],
                            entity["type"],
                            entity["properties"]["CIDR"],
                        )
                    else:  # start/end instead of cidr
                        print(
                            server["name"],
                            prop["fullHostName"],
                            prop["defaultInterfaceAddress"],
                            role["type"],
                            entity["type"],
                            entity["properties"]["start"],
                            entity["properties"]["end"],
                        )
                elif entity["type"] in ("IP6Network", "IP6Block"):
                    print(
                        server["name"],
                        prop["fullHostName"],
                        prop["defaultInterfaceAddress"],
                        role["type"],
                        entity["type"],
                        entity["properties"]["prefix"],
                    )
                else:
                    print(
                        server["name"],
                        prop["fullHostName"],
                        prop["defaultInterfaceAddress"],
                        role["type"],
                        entity["type"],
                        "unknown-type",
                    )


if __name__ == "__main__":
    main()
