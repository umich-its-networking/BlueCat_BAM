#!/usr/bin/env python

"""
delete_dhcp_reserved_by_network.py < list-of-networkIP
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging

import bluecat_bam


__progname__ = "delete_dhcp_reserved_by_network"
__version__ = "0.1"


def get_bam_api_list(conn, apiname, **kwargs):
    """wrap api call with loop to handle 'start' and 'count'"""
    if not kwargs["count"]:
        kwargs["count"] = 1000
    if not kwargs["start"]:
        kwargs["start"] = 0
    count = kwargs["count"]
    replysize = count
    listall = []
    start = 0
    while replysize == count:
        kwargs["start"] = start
        listone = conn.do(apiname, **kwargs)
        replysize = len(listone)
        start += replysize
        # print(replysize)
        listall.extend(listone)
    return listall


def get_dhcp_reserved(networkid, conn):
    """get list of entities"""
    logger = logging.getLogger()
    # ip_list = conn.do(
    ip_list = get_bam_api_list(
        conn,
        "getEntities",
        parentId=networkid,
        type="IP4Address",
        start=0,
        count=1000,
    )
    logger.info(ip_list)
    reserved_list = [
        ip for ip in ip_list if ip["properties"]["state"] == "DHCP_RESERVED"
    ]
    print("dhcp", len(ip_list), "reserved", len(reserved_list), file=sys.stderr)
    return reserved_list


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
    """delete_dhcp_reserved_by_network.py"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    object_ident = args.object_ident
    rangetype = ""

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        obj_list = conn.get_obj_list(conn, object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for entity in obj_list:
            entityId = entity["id"]

            reserved_list = get_dhcp_reserved(entityId, conn)
            for ip in reserved_list:
                print_ip(ip)
                # result = conn.do("delete", objectId=ip["id"])
                result = conn.do(
                    "deleteWithOptions",
                    method="delete",
                    objectId=ip["id"],
                    options="noServerUpdate=true|deleteOrphanedIPAddresses=true|",
                )
                if result:
                    print("result: ", result)


def print_ip(ip):
    """print ip address object"""
    name = getfield(ip, "name")
    address = getprop(ip, "address")
    mac = getprop(ip, "macAddress")
    print(address, name, mac)


if __name__ == "__main__":
    main()
