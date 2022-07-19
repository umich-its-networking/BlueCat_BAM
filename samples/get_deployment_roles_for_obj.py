#!/usr/bin/env python

"""
get_deployment_roles_for_obj.py  server-name
[--cfg configuration] [--view viewname]

For given DNS server,
list the DNS roles
"""

# to be python2/3 compatible:
from __future__ import print_function

import logging
import bluecat_bam


__progname__ = "get_deployment_roles_for_obj.py"
__version__ = "0.1"


def main():
    """get_deployment_roles_for_obj where obj is block, network, zone, etc"""
    config = bluecat_bam.BAM.argparsecommon(
        "get_deployment_roles_for_obj where obj is block, network, zone, etc"
    )
    config.add_argument(
        "object",
        help="block or network CIDR, zone name, or any object_id, or filename",
    )
    config.add_argument("--service", help="optional: DNS, DHCP, DHCP6, TFTP, etc")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration, args.view)

        obj_list = conn.get_obj_list(args.object, configuration_id, "")

        for obj in obj_list:
            get_deployment_roles(obj, conn, args)


def get_deployment_roles(obj, conn, args):
    """get deployment roles for obj"""
    roles = conn.do("getDeploymentRoles", entityId=obj["id"])
    # print(obj)
    name = obj.get("name") or ""
    out = "{} {} {} {} {}".format(
        obj["type"],
        name,
        obj["id"],
        obj["properties"].get("CIDR"),
        obj["properties"].get("sharedNetwork"),
    )
    print(out)
    outlist = []
    for role in roles:
        # print("    ",role)
        role_service = role["service"]
        if args.service is None or args.service == role_service:
            role_server = conn.do("getEntityById", id=role["serverInterfaceId"])
            out = "    {} {} {}".format(role_service, role["type"], role_server["name"])
            # print(out)
            outlist.append(out)
            # check for secondary DHCP server
            sec = role["properties"].get("secondaryServerInterfaceId")
            if sec:
                role_server = conn.do("getEntityById", id=sec)
                out = "    {} {} {}".format(
                    role["service"], "SLAVE", role_server["name"]
                )
                # print(out)
                outlist.append(out)
    for out in sorted(outlist):
        print(out)


if __name__ == "__main__":
    main()