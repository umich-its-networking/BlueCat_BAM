#!/usr/bin/env python

"""
add_DHCP_deployment_option.py entity optionname optionvalue --properties properties
"""

# add_DHCP_deployment_option.py 8246503 vendor-encapsulated-options F1:04:8D:D5:98:4B
# {"id": 22348235, "type": "DHCPClient", "name": "vendor-encapsulated-options",
# "value": "F1:04:8D:D5:98:4B", "properties": {"inherited": "false"}}

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging
import re

import bluecat_bam


__progname__ = "add_DHCP_deployment_option"
__version__ = "0.1"


def getserverid(server_name, configuration_id, conn):
    """get server id, given the server domainname or displayname"""
    # try by the server domainname
    interface_obj_list = conn.do(
        "searchByObjectTypes",
        keyword=server_name,
        types="NetworkServerInterface",
        start=0,
        count=2,  # error if more than one
    )
    if len(interface_obj_list) > 1:
        print(
            "ERROR - more than one server interface found",
            json.dumps(interface_obj_list),
        )
        sys.exit(3)
    interfaceid = interface_obj_list[0]["id"]
    if interfaceid != 0:
        obj = conn.do("getParent", entityId=interfaceid)
        return obj["id"]
    # server not found by domanname
    # try by the server display name
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
    return server_id


def get_range(conn, address, configuration_id, rangetype):
    """get range - block, network, or dhcp range - by ip"""
    logger = logging.getLogger()
    logger.info("get_range: %s", address)
    obj = conn.do(
        "getIPRangedByIP", address=address, containerId=configuration_id, type=rangetype
    )
    # print(json.dumps(obj))
    obj_id = obj["id"]

    logging.info("getIPRangedByIP obj = %s", json.dumps(obj))
    if obj_id == 0:
        print("Not found")
        obj = None
    else:
        # bug in BlueCat - if Block and Network have the same CIDR,
        # it should return the Network, but it returns the Block.
        # So check for a matching Network.
        if rangetype == "" and obj["type"] == "IP4Block":
            cidr = obj["properties"]["CIDR"]
            network_obj = conn.do(
                "getEntityByCIDR",
                method="get",
                cidr=cidr,
                parentId=obj_id,
                type="IP4Network",
            )
            if network_obj["id"]:
                obj = network_obj
                logger.info("IP4Network found: %s", obj)
    return obj


def get_id(conn, object_ident, configuration_id, rangetype):
    """get id for a particular object"""
    logger = logging.getLogger()
    id_pattern = re.compile(r"\d+$")
    id_match = id_pattern.match(object_ident)
    logger.info("id Match result: %s", id_match)
    if id_match:  # an id
        obj_id = object_ident
    else:  # not an id
        ip_pattern = re.compile(r"((?:\d{1,3}\.){3}\d{1,3})($|[^\d])")
        ip_match = ip_pattern.match(object_ident)
        logger.info("IP Match result: '%s'", ip_match)
        if ip_match:  # an IP
            logger.info("IP Match: '%s' and '%s'", ip_match.group(1), ip_match.group(2))
            object_ident = ip_match.group(1)
            if not rangetype:
                if ip_match.group(2) == "":
                    rangetype = "IP4Address"
                elif ip_match.group(2) == "-":
                    rangetype = "DHCP4Range"
                # "/" matches either IP4Block or IP4Network
            if rangetype == "IP4Address":
                obj = conn.do(
                    "getIP4Address",
                    method="get",
                    containerId=configuration_id,
                    address=object_ident,
                )
            else:
                obj = get_range(conn, object_ident, configuration_id, rangetype)
            obj_id = obj.get("id")
        else:  # not and IP or id
            obj_id = None
    logger.info("get_id returns %s of type %s", obj, rangetype)
    return obj_id


def get_id_list(conn, object_ident, configuration_id, rangetype):
    """get object, or a list of objects from a file"""
    obj_id = get_id(conn, object_ident, configuration_id, rangetype)
    if obj_id:
        id_list = [obj_id]
    else:  # not an IP or id, must be a file name
        with open(object_ident) as f:
            id_list = [
                get_id(conn, line.strip(), configuration_id, rangetype)
                for line in f
                if line.strip() != ""
            ]
    return id_list


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
    """
    add_DHCP_deployment_option.py entityId optionname optionvalue -p properties
    """
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "entityId",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename with any of those on each line"
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument("optionname")
    config.add_argument("optionvalue")
    config.add_argument(
        "--dhcpserver", help="name of DHCP server, if option only applies to one server"
    )
    config.add_argument(
        "--properties", help='other properties as a JSON dict "{name: value}"'
    )
    config.add_argument(
        "--type",
        help='limit to a specific type: "IP4Address", "IP4Block", "IP4Network", '
        + 'or "DHCP4Range"',
        default="",
    )
    config.add_argument(
        "--service",
        help="add a DHCP SERVICE Deployment Option "
        + "(default is a DHCP CLIENT Deployment Option)",
        action="store_true",
    )

    args = config.parse_args()

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

        if args.properties:
            prop = bluecat_bam.BAM.convert_dict_in_str_to_dict(args.properties)
        else:
            prop = {}

        # print(prop)
        dhcpserver_id = 0
        if args.dhcpserver:
            dhcpserver_id = getserverid(args.dhcpserver, configuration_id, conn)
            prop["server"] = dhcpserver_id
        # print(prop)

        object_ident = args.entityId
        obj_list = get_id_list(conn, object_ident, configuration_id, args.type)
        logger.info(obj_list)

        for entityId in obj_list:
            entity = conn.do("getEntityById", id=entityId)
            # print("Entity found:")
            # print(entity)
            objtype = getfield(entity, "type")
            name = getfield(entity, "name")

            print(
                "For entity: ",
                objtype,
                name,
                getprop(entity, "CIDR"),
                getprop(entity, "start"),
                getprop(entity, "end"),
            )

            # print("adding deployment option:")
            if args.service:
                api = "addDHCPServiceDeploymentOption"
                api2 = "getDHCPServiceDeploymentOption"
            else:
                api = "addDHCPClientDeploymentOption"
                api2 = "getDHCPClientDeploymentOption"
            obj_id = conn.do(
                api,
                entityId=entityId,
                name=args.optionname,
                value=args.optionvalue,
                properties=prop,
            )

            logger.info(obj_id)

            option = conn.do(
                api2,
                entityId=entityId,
                name=args.optionname,
                serverId=dhcpserver_id,
            )
            # print(json.dumps(option))
            objtype = getfield(option, "type")
            name = getfield(option, "name")
            value = getfield(option, "value")
            inherited = getprop(option, "inherited")
            print("    Added deployment option:", objtype, name, value, inherited)


if __name__ == "__main__":
    main()
