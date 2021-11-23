#!/usr/bin/env python

"""
delete_lease_time.py entity
"""

# delete_lease_time.py 8246503
# {"id": 22348235, "type": "DHCPClient", "name": "vendor-encapsulated-options",
# "value": "F1:04:8D:D5:98:4B", "properties": {"inherited": "false"}}

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging

import bluecat_bam


__progname__ = "delete_lease_time"
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


def getfield(obj, fieldname):
    """get a field for printing"""
    field = str(obj.get(fieldname))
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
    delete_lease_time.py entityId
    """
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument(
        "--dhcpserver", help="name of DHCP server, if option only applies to one server"
    )
    config.add_argument(
        "--type",
        help='limit to a specific type: "IP4Address", "IP4Block", "IP4Network", '
        + 'or "DHCP4Range"',
        default="",
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

        dhcpserver_id = 0
        if args.dhcpserver:
            dhcpserver_id = getserverid(args.dhcpserver, configuration_id, conn)

        object_ident = args.object_ident
        entity_list = conn.get_obj_list(conn, object_ident, configuration_id, args.type)
        logger.info(entity_list)

        for entity in entity_list:
            entity_id = entity.get("id")
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

            optionlist = ["default-lease-time", "max-lease-time", "min-lease-time"]
            for opt_name in optionlist:
                option = conn.do(
                    "getDHCPServiceDeploymentOption",
                    entityId=entity_id,
                    name=opt_name,
                    serverId=dhcpserver_id,
                )
                logger.info(json.dumps(option))
                if option.get("id") == 0:
                    print("no option", opt_name, "at this level, cannot delete")
                else:
                    objtype = getfield(option, "type")
                    name = getfield(option, "name")
                    value = getfield(option, "value")
                    inherited = getprop(option, "inherited")
                    print(
                        "    deleting deployment option:",
                        objtype,
                        name,
                        value,
                        inherited,
                    )
                    result = conn.do("delete", objectId=option["id"])
                    if result:
                        print("result: ", result)

            options = conn.do(
                "getDeploymentOptions",
                entityId=entity_id,
                optionTypes="DHCPServiceOption",
                serverId=-1,
            )
            logger.info(json.dumps(options))
            printoptions(options, optionlist)


def printoptions(options, optionlist):
    """print options"""
    print("Options are now:")
    for option in options:
        if optionlist and option.get("name") not in optionlist:
            continue
        opt_id = getfield(option, "id")
        objtype = getfield(option, "type")
        name = getfield(option, "name")
        value = getfield(option, "value")
        inherited = getprop(option, "inherited")
        print("    ", opt_id, objtype, name, value, inherited)


if __name__ == "__main__":
    main()
