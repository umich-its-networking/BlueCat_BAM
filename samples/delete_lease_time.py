#!/usr/bin/env python

"""
delete_lease_time.py entity
"""

# delete_lease_time.py 8246503
# {"id": 22348235, "type": "DHCPClient", "name": "vendor-encapsulated-options",
# "value": "F1:04:8D:D5:98:4B", "properties": {"inherited": "false"}}

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging

import bluecat_bam


__progname__ = "delete_lease_time"
__version__ = "0.1"


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
            server_obj, _ = conn.getserver(args.dhcpserver, configuration_id)
            dhcpserver_id = server_obj["id"]

        object_ident = args.object_ident
        entity_list = conn.get_obj_list(object_ident, configuration_id, args.type)
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
                if not option.get("id"):
                    print("no option", opt_name, "at this level, cannot delete")
                else:
                    print(
                        "    deleting %s: type %s,\tname %s,\tvalue %s,\tinherited %s"
                        % (
                            "deployment option",
                            option["type"],
                            option["name"],
                            option["value"],
                            option["properties"]["inherited"],
                        )
                    )
                    result = conn.do("delete", objectId=option["id"])
                    if result:
                        print("result: ", result)

            for opt_name in optionlist:
                option = conn.do(
                    "getDHCPServiceDeploymentOption",
                    entityId=entity_id,
                    name=opt_name,
                    serverId=dhcpserver_id,
                )
                logger.info(json.dumps(option))
                if option.get("id"):
                    print(
                        "    id %s,\ttype %s,\tname %s,\tvalue %s,\tinherited %s"
                        % (
                            option["id"],
                            option["type"],
                            option["name"],
                            option["value"],
                            option["properites"]["inherited"],
                        )
                    )


if __name__ == "__main__":
    main()
