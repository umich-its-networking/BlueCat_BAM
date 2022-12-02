#!/usr/bin/env python

"""
add_DHCP_deployment_option.py entity optionname optionvalue --properties properties
"""

# add_DHCP_deployment_option.py 8246503 vendor-encapsulated-options F1:04:8D:D5:98:4B
# {"id": 22348235, "type": "DHCPClient", "name": "vendor-encapsulated-options",
# "value": "F1:04:8D:D5:98:4B", "properties": {"inherited": "false"}}

# to be python2/3 compatible:
from __future__ import print_function

import logging

import bluecat_bam


__progname__ = "add_DHCP_deployment_option"
__version__ = "0.1"


def getfield(obj, fieldname):
    """get a field for printing"""
    field = obj.get(fieldname)
    if field:
        output = fieldname + ": " + field + ",\t"
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
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
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

        if args.properties:
            prop = bluecat_bam.BAM.convert_dict_in_str_to_dict(args.properties)
        else:
            prop = {}

        # print(prop)
        dhcpserver_id = 0
        if args.dhcpserver:
            server_obj, _ = conn.getserver(args.dhcpserver, configuration_id)
            dhcpserver_id = server_obj["id"]
            prop["server"] = dhcpserver_id
        # print(prop)

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

            # print("adding deployment option:")
            if args.service:
                api = "addDHCPServiceDeploymentOption"
                api2 = "getDHCPServiceDeploymentOption"
            else:
                api = "addDHCPClientDeploymentOption"
                api2 = "getDHCPClientDeploymentOption"
            option_id = conn.do(
                api,
                entityId=entity_id,
                name=args.optionname,
                value=args.optionvalue,
                properties=prop,
            )
            logger.info(option_id)

            option = conn.do(
                api2,
                entityId=entity_id,
                name=args.optionname,
                serverId=dhcpserver_id,
            )
            print(
                "    Added %s: type %s,\tname %s,\tvalue %s,\tinherited %s"
                % (
                    "deployment option",
                    option["type"],
                    option["name"],
                    option["value"],
                    option["properties"]["inherited"],
                )
            )


if __name__ == "__main__":
    main()
