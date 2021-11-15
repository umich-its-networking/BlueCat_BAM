#!/usr/bin/env python

"""
change_to_dhcp_reserved.py < list-of-networkIP
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging

import bluecat_bam


__progname__ = "change_to_dhcp_reserved"
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


def get_ip_by_state(networkid, conn, state):
    """get list of IP objects matching state"""
    logger = logging.getLogger()
    ip_list = get_bam_api_list(
        conn,
        "getEntities",
        parentId=networkid,
        type="IP4Address",
        start=0,
        count=1000,
    )
    logger.debug(ip_list)
    matching_list = [ip for ip in ip_list if ip["properties"]["state"] == state]
    return matching_list


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
    """change_to_dhcp_reserved.py"""
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
            matching_list = get_ip_by_state(entityId, conn, "DHCP_ALLOCATED")
            for ip in matching_list:
                obj_id = ip["id"]
                obj_mac = ip["properties"]["macAddress"]
                result = conn.do(
                    "changeStateIP4Address",
                    addressId=obj_id,
                    macAddress=obj_mac,
                    targetState="MAKE_DHCP_RESERVED",
                )
                if result:
                    print("result:", result)
                ip = conn.do("getEntityById", id=obj_id)
                print(
                    getfield(ip, "name"),
                    getprop(ip, "address"),
                    getprop(ip, "macAddress"),
                )


if __name__ == "__main__":
    main()
