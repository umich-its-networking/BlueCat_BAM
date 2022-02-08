#!/usr/bin/env python

"""
add_lease_time.py entity leasetime
"""

# add_lease_time.py 8246503 1800
# {"id": 22348235, "type": "DHCPClient", "name": "vendor-encapsulated-options",
# "value": "F1:04:8D:D5:98:4B", "properties": {"inherited": "false"}}

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging

import bluecat_bam


__progname__ = "add_lease_time"
__version__ = "0.1"


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
    """add_lease_time.py entityId leasetime"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument("leasetime")
    config.add_argument(
        "--dhcpserver", help="name of DHCP server, if option only applies to one server"
    )
    config.add_argument(
        "--type",
        help='limit to a specific type: "IP4Address", "IP4Block", "IP4Network", '
        + 'or "DHCP4Range"',
        default="",
    )
    config.add_argument(
        "--quiet",
        "-q",
        help="return a status code (non-zero = error) and only print warnings",
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

        prop = {}
        dhcpserver_id = 0
        if args.dhcpserver:
            server_obj, _ = conn.getserver(args.dhcpserver, configuration_id)
            dhcpserver_id = server_obj["id"]
            prop["server"] = dhcpserver_id
        # print(prop)

        object_ident = args.object_ident
        entity_list = conn.get_obj_list(object_ident, configuration_id, args.type)
        logger.info(entity_list)

        result = True
        for entity in entity_list:
            result1 = add_lease_time_to_entity(entity, args, conn, prop, dhcpserver_id)
            if result1 == 1:
                result = 1  # Failed
        return result


def add_lease_time_to_entity(entity, args, conn, prop, dhcpserver_id):
    """add lease time"""
    logger = logging.getLogger()
    result=True
    entity_id = entity.get("id")
    if not args.quiet:
        print(
            "For entity: ",
            getfield(entity, "type"),
            getfield(entity, "name"),
            getprop(entity, "CIDR"),
            getprop(entity, "start"),
            getprop(entity, "end"),
        )

    for opt_name in ["default-lease-time", "max-lease-time", "min-lease-time"]:
        option = conn.do(
            "getDHCPServiceDeploymentOption",
            entityId=entity_id,
            name=opt_name,
            serverId=dhcpserver_id,
        )
        logger.info(option)
        if option.get("id"):
            value = option["value"]
            if not args.quiet:
                print("option", opt_name, "already set to", value)
            if value != args.leasetime:
                result = False
                print(
                    "ERROR - failed to set",
                    getfield(option, "name"),
                    file=sys.stderr,
                )
        else:
            option_id = conn.do(
                "addDHCPServiceDeploymentOption",
                entityId=entity_id,
                name=opt_name,
                value=args.leasetime,
                properties=prop,
            )
            logger.info(option_id)

            option = conn.do(
                "getDHCPServiceDeploymentOption",
                entityId=entity_id,
                name=opt_name,
                serverId=dhcpserver_id,
            )
            logger.info(json.dumps(option))
            if not args.quiet:
                objtype = getfield(option, "type")
                name = getfield(option, "name")
                value = getfield(option, "value")
                inherited = getprop(option, "inherited")
                print(
                    "    Added deployment option:",
                    objtype,
                    name,
                    value,
                    inherited,
                )
            if option["value"] != args.leasetime:
                result = False
                print(
                    "ERROR - failed to set",
                    getfield(option, "name"),
                    file=sys.stderr,
                )
                # break   # skip rest of options for this entity

    if result:
        return 0  # success
    return 1  # failed


if __name__ == "__main__":
    resultm = main()
    sys.exit(resultm)
