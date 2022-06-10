#!/usr/bin/env python

"""
change_from_dhcp_reserved.py < list-of-networkIP
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging

import bluecat_bam


__progname__ = "change_from_dhcp_reserved"
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
    print("dhcp", len(ip_list), "reserved", len(reserved_list))
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
    """change_from_dhcp_reserved.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Replace DHCP Reserved records with DHCP Allocated, and recreate any HostRecord"
    )
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

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=args.configuration,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        obj_list = conn.get_obj_list(args.object_ident, configuration_id, "")
        logger.info("obj_list: %s", obj_list)

        for entity in obj_list:
            entityId = entity["id"]

            reserved_list = get_dhcp_reserved(entityId, conn)
            for ip in reserved_list:
                print_ip(ip)
                # check if in DHCP Range

                # save and restore host records
                hostrec_list = conn.do(
                    "getLinkedEntities",
                    entityId=ip["id"],
                    type="HostRecord",
                    start=0,
                    count=1000,
                )
                # get view of each record
                hostrec_view_dict = {}
                for host_obj in hostrec_list:
                    host_id = host_obj["id"]
                    logger.info("host_id %s", host_id)
                    hostrec_view_dict[host_id] = conn.getparentview(host_id)

                result = conn.do("delete", objectId=ip["id"])
                if result:
                    print("result: ", result)
                hostname_list = []
                for host_obj in hostrec_list:
                    view_id = hostrec_view_dict[host_id]
                    result = conn.do(
                        "addHostRecord",
                        absoluteName=host_obj["properties"]["absoluteName"],
                        addresses=host_obj["properties"]["addresses"],
                        properties="",
                        ttl=host_obj["properties"].get("ttl", "-1"),
                        viewId=view_id,
                    )
                    if result:
                        print("addHostRecord result", result)
                    # or assignIP4Address  ??
                    hostname_list.append(host_obj["properties"]["absoluteName"])
                hostname_out = " ".join(hostname_list)
                if hostname_list:
                    print(hostname_out)


def print_ip(ip):
    """print ip address object"""
    name = getfield(ip, "name")
    address = getprop(ip, "address")
    mac = getprop(ip, "macAddress")
    print(address, name, mac)


if __name__ == "__main__":
    main()
