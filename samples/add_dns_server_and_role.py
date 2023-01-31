#!/usr/bin/env python

"""
add_dns_server_and_role.py zone servername serverip [role [profile]]
Create server object then add DNS deployment role to zone
Intended for DNS servers that are separate for every zone
role defaults to SLAVE
profile defaults to OTHER_DNS_SERVER
Does not create a Host Record for the server
Prints the server object, the NetworkServerInterface object, and the DNS role object
"""

# to be python2/3 compatible:
from __future__ import print_function

import logging

import bluecat_bam


__progname__ = "add_dns_server_and_role"
__version__ = "0.1"


def main():
    """
    add_dns_server_and_role.py zone servername serverip [role [profile]]
    """
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument("zone")
    config.add_argument("servername")
    config.add_argument("serverip")
    config.add_argument("role", default="SLAVE")
    config.add_argument("profile", default="OTHER_DNS_SERVER")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, view_id) = conn.get_config_and_view(
            args.configuration, args.view
        )

        serverid = conn.do(
            "addServer",
            configurationId=configuration_id,
            defaultInterfaceAddress=args.serverip,
            fullHostName=args.servername,
            name=args.servername,
            profile=args.profile,
        )

        serverobj = conn.do("getEntityById", id=serverid)
        print(serverobj)

        interfacelist = conn.do(
            "getEntities",
            type="NetworkServerInterface",
            parentId=serverid,
            start=0,
            count=1000,
        )
        if len(interfacelist) != 1:
            print("error - interface list not length one", interfacelist)
            return

        interfaceobj = interfacelist[0]
        print(interfaceobj)
        interfaceid = interfaceobj["id"]

        zone_obj, remainder = conn.get_zone(args.zone, view_id)
        if remainder:
            print(f"zone not found, only found: {zone_obj}, not found: {remainder}")
            return
        print(zone_obj)
        zoneid = zone_obj["id"]

        roleid = conn.do(
            "addDNSDeploymentRole",
            entityId=zoneid,
            serverInterfaceId=interfaceid,
            type=args.role,
        )

        roleobj = conn.do("getEntityById", id=roleid)
        print(roleobj)


if __name__ == "__main__":
    main()
