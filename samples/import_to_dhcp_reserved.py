#!/usr/bin/env python

"""
import_to_dhcp_reserved.py < output-from-arubaIntermapperSnmp
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import re
import json
import itertools

import bluecat_bam


__progname__ = "import_to_dhcp_reserved"
__version__ = "0.1"


def get_ip_list(networkid, conn):
    """get list of IP objects"""
    logger = logging.getLogger()
    ip_list = conn.get_bam_api_list(
        "getEntities",
        parentId=networkid,
        type="IP4Address",
    )
    logger.debug(ip_list)
    return ip_list


def set_name(conn, ip_obj, name):
    """set name"""
    if name:
        ip_obj["name"] = name
        result = conn.do("update", method="put", data=ip_obj)
        if result:
            print(result)
        ip_obj = conn.do("getEntityById", method="get", id=ip_obj["id"])
    return ip_obj


def do_checkonly(counts, line, line_mac, ip_obj, obj_mac, obj_state):
    """checkonly mode"""
    logger = logging.getLogger()
    logger.info(
        "line_mac %s, ip_obj %s, obj_state %s", line_mac, json.dumps(ip_obj), obj_state
    )
    if not ip_obj:
        print(line, "not in BlueCat")
        counts["importonly"] += 1
    elif not line_mac:
        print(line, "no mac in import")
        counts["importnomac"] += 1
    elif obj_state in ("DHCP_ALLOCATED", "DHCP_RESERVED"):
        if obj_mac and line_mac == obj_mac:
            print(line, "MAC Address matches")
            counts["macsame"] += 1
        else:
            print(line, "MAC Address different")
            counts["macdiff"] += 1
    else:
        print(line, "free in BlueCat")
        counts["dhcpfree"] += 1


def make_dhcp_reserved(conn, ip, mac, name, fqdn, configuration_id, view_id):
    """make dchp reserved"""
    logger = logging.getLogger()
    if fqdn:
        hostinfo_list = [
            fqdn,
            str(view_id),
            "reverseFlag=true",
            "sameAsZoneFlag=false",
        ]
        hostinfo = ",".join(hostinfo_list)
    else:
        hostinfo = ""
    new_ip_id = conn.do(
        "assignIP4Address",
        method="post",
        configurationId=configuration_id,
        ip4Address=ip,
        macAddress=mac,
        hostInfo=hostinfo,
        action="MAKE_DHCP_RESERVED",
        properties="",
    )
    # print(new_ip_id)
    ip_obj = conn.do("getEntityById", id=new_ip_id)
    logger.info(json.dumps(ip_obj))

    # cannot set object name in previous call, so update it with the name
    if name:
        ip_obj = set_name(conn, ip_obj, name)
    logger.info(json.dumps(ip_obj))
    return ip_obj


def canonical_mac(mac):
    """convert MAC Address to lowercase with no punctuation
    so that it can be compared to another MAC Address"""
    cmac = "".join([c.lower() for c in mac if c in "0123456789abcdefABCDEF"])
    return cmac


def main():
    """import_to_dhcp_reserved.py"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument(
        "inputfile",
        help="<inputfile> format: IP MAC-Address ipname DNS-name"
        + " only IP is required.  MAC will be taken from existing record if not given."
        + " Host Record will be created/updated if DNS-name (fqdn) is given."
        + " Fields can be separated by tabs, spaces, or commas."
        + " Extra fields will be ignored.  ipname cannot have spaces.",
    )
    config.add_argument(
        "--checkmac",
        action="store_true",
        help="verify that the mac address in the import file matches the "
        + "mac address in the IP object, otherwise skip it",
    )
    config.add_argument(
        "--checkonly",
        action="store_true",
        help="verify that the IP and mac addresses in the import file match"
        + " the BAM, but do not change anything.",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, view_id) = conn.get_config_and_view(
            args.configuration, args.view
        )

        ip_dict = make_ip_dict(conn, args.object_ident, configuration_id)
        logger.info("ip_dict %s", json.dumps(ip_dict))
        counts = {
            "importonly": 0,
            "importnomac": 0,
            "macdiff": 0,
            "macsame": 0,
            "dhcpfree": 0,
        }

        # {"id": 17396816, "name": "MYPC-1450", "type": "IP4Address",
        # "properties": {"address": "10.0.1.244", "state":
        # "DHCP_RESERVED", "macAddress": "DE-AD-BE-EF-16-E8"}}
        # # ip_obj = {"name": "", "properties": {"address":"","state":
        # "", "macAddress": ""}}

        # now read the data from csv file from controller
        line_pat = re.compile(r"((?:\d{1,3}\.){3}\d{1,3})($| |\t|,)")
        with open(args.inputfile) as f:
            for line in f:
                line = line.strip()

                # get import file info
                line_d = parse_line(line, line_pat)
                if not line_d:
                    continue
                line_mac = canonical_mac(line_d["mac"])

                # get BlueCat info
                ip_obj = ip_dict.get(line_d["ip"])
                if not ip_obj:
                    obj_mac = None
                    obj_state = None
                    logger.info("ip %s not found in ip_dict", line_d["ip"])
                else:
                    obj_mac = canonical_mac(ip_obj["properties"].get("macAddress"))
                    obj_state = ip_obj["properties"].get("state")
                    logger.info(
                        "found ip %s in ip_dict, mac %s, state %s",
                        line_d["ip"],
                        obj_mac,
                        obj_state,
                    )

                # possible conditions:
                # ip in import file, but not BlueCat (create new)
                # ip is DHCP_ALLOCATED or DHCP_RESERVED and:
                #      mac is different (warn, update if forced?)
                #      mac is same (update other info)
                # ip is DHCP_FREE or other (update)

                # for checkonly mode:
                # import file does not have mac - warn and skip
                # ip in import file, but not BlueCat - warn
                # ip is DHCP_ALLOCATED or DHCP_RESERVED and:
                #      mac is different - error
                #      mac is same - ok
                # ip is DHCP_FREE or other - warn

                if args.checkonly:
                    do_checkonly(counts, line, line_mac, ip_obj, obj_mac, obj_state)
                    continue

                # not in checkonly node, take action
                do_action(
                    conn,
                    ip_obj,
                    line,
                    line_d,
                    line_mac,
                    obj_state,
                    configuration_id,
                    view_id,
                    args,
                )


def do_action(
    conn, ip_obj, line, line_d, line_mac, obj_state, configuration_id, view_id, args
):
    """update or add dhcp reserved"""
    logger = logging.getLogger()
    if not ip_obj:
        logger.info("not found in range, so create new")

        if not line_mac:
            print("no MAC Address in BlueCat or input line:", line)
            return

        ip_obj = make_dhcp_reserved(
            conn,
            line_d["ip"],
            line_mac,
            line_d["name"],
            line_d["fqdn"],
            configuration_id,
            view_id,
        )
    else:
        # convert and update existing IP

        # first get mac address object
        line_mac = get_either_mac(line_mac, conn, configuration_id, ip_obj, args)
        if not line_mac:
            print("ERROR - no mac in import or BlueCat")
            return
        if obj_state in ("DHCP_ALLOCATED", "STATIC"):
            update_dhcp_allocated(conn, ip_obj, line_mac, line_d["name"])

        elif obj_state == "DHCP_FREE":
            replace_dhcp_free(
                conn,
                ip_obj,
                line_d["ip"],
                line_mac,
                line_d["name"],
                line_d["fqdn"],
                configuration_id,
                view_id,
            )

        elif obj_state == "DHCP_RESERVED":
            update_dhcp_reserved(conn, ip_obj, line_mac, line_d["name"])

        else:
            print("error - cannot handle state:", obj_state)

    # fqdn
    do_fqdn(conn, line_d["fqdn"], line_d["ip"], view_id, line)

    final_ip_obj = conn.do("getEntityById", id=ip_obj["id"])
    print(final_ip_obj)


def do_fqdn(conn, line_fqdn, line_ip, view_id, line):
    """check or create host record"""
    if line_fqdn:
        fqdn_objs = conn.get_fqdn(line_fqdn, view_id)
        if fqdn_objs:
            if len(fqdn_objs) > 1:
                print(
                    "error, more than one fqdn found, please fix by hand",
                    line,
                )
            else:
                fqdn = fqdn_objs[0]
                fqdn_id = fqdn["id"]
                if line_ip != fqdn["properties"]["addresses"]:
                    fqdn["properties"]["addresses"] = line_ip
                    result = conn.do("update", body=fqdn)
                    if result:
                        print("host record update result: ", result)
                    print("updated", json.dumps(fqdn))
        else:
            fqdn_id = conn.do(
                "addHostRecord",
                absoluteName=line_fqdn,
                addresses=line_ip,
                ttl=-1,
                viewId=view_id,
            )
            fqdn = conn.do(
                "getEntityById",
                id=fqdn_id,
            )
        print(fqdn)


def parse_line(line, line_pat):
    """parse the input line into a dict"""
    logger = logging.getLogger()
    if line == "":  # skip blank lines
        return None
    # match IP Address and the following delimiter
    line_match = line_pat.match(line)
    if not line_match:
        print("did not find IP and delimiter in line:", line)
        return None
    delimiter = line_match.group(2)
    if delimiter:  # if line had only the ip and no delimiter
        delimiter = ","  # just need some delimiter for split
    line_d = dict(
        itertools.zip_longest(
            ["ip", "mac", "name", "fqdn", "other"], line.split(delimiter, 5)
        )
    )
    if line_d["fqdn"]:
        # pattern from:
        # https://www.geeksforgeeks.org/how-to-validate-a-domain-name-using-regular-expression/
        dom_match = re.match(
            r"^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$", line_d["fqdn"]
        )
        if not dom_match:
            print("not a valid domain name:", line_d["fqdn"])
            return None
    logger.info("ip,mac,name,fqdn,other: %s", json.dumps(line_d))
    return line_d


def make_ip_dict(conn, object_ident, configuration_id):
    """make ip dict"""
    logger = logging.getLogger()
    obj_list = conn.get_obj_list(conn, object_ident, configuration_id, "")
    logger.info("obj_list: %s", json.dumps(obj_list))
    ip_dict = {}
    for entity in obj_list:
        entityId = entity["id"]
        matching_list = get_ip_list(entityId, conn)
        for ip in matching_list:
            ip_address = ip["properties"]["address"]
            ip_dict[ip_address] = ip
    return ip_dict


def get_either_mac(line_mac, conn, configuration_id, ip_obj, args):
    """get mac from input line or from existing IP object"""
    logger = logging.getLogger()
    logger.info("line_mac %s", line_mac)
    ip_obj_mac = canonical_mac(ip_obj["properties"].get("macAddress"))
    logger.info("ip_obj_mac %s", ip_obj_mac)
    if line_mac:
        if ip_obj_mac and args.checkmac and line_mac != ip_obj_mac:
            print("error --checkmac specified but mac addresses do not match")
            print("mac address from input line:", line_mac)
            print("mac address from ip object: ", ip_obj_mac)
            return None
        mac_obj = get_mac(conn, configuration_id, line_mac)
        if mac_obj:
            print("found mac", mac_obj)
    else:  # no mac in import data, find in bam
        if ip_obj_mac:
            line_mac = ip_obj_mac
        else:
            print("error - no MAC Address in existing IP or in import line")
    return line_mac


def get_mac(conn, configuration_id, mac):
    """check if mac object exists in bam"""
    mac_obj = conn.do(
        "getMACAddress",
        method="get",
        configurationId=configuration_id,
        macAddress=mac,
    )
    if mac_obj["id"] == 0:
        print("no current mac address object for", mac)
        return None
    return mac_obj


def update_dhcp_allocated(conn, ip_obj, line_mac, line_name):
    """update dhcp allocated"""
    logger = logging.getLogger()
    result = conn.do(
        "changeStateIP4Address",
        addressId=ip_obj["id"],
        macAddress=line_mac,
        targetState="MAKE_DHCP_RESERVED",
    )
    if result:
        print("changestate result:", result)
    new_ip_obj = conn.do(
        "getEntityById",
        id=ip_obj["id"],
    )
    logger.info("new %s", json.dumps(new_ip_obj))
    ip_obj = new_ip_obj

    # update the name (cannot be done in the above API)
    if line_name:
        set_name(conn, ip_obj, line_name)


def replace_dhcp_free(
    conn, ip_obj, line_ip, line_mac, line_name, line_fqdn, configuration_id, view_id
):
    """replace dhcp free"""
    # cannot convert directly to reserved, so delete, and recreate
    result = conn.do(
        "delete",
        objectId=ip_obj["id"],
    )
    if result:
        print("deleting DHCP_FREE result:", result)
    ip_obj = make_dhcp_reserved(
        conn,
        line_ip,
        line_mac,
        line_name,
        line_fqdn,
        configuration_id,
        view_id,
    )
    print("replaced with:", ip_obj)


def update_dhcp_reserved(conn, ip_obj, line_mac, line_name):
    """update dhcp reserved"""
    update = False
    if ip_obj["properties"]["macAddress"] != line_mac:
        update = True
        ip_obj["properties"]["macAddress"] = line_mac
    if line_name and line_name != ip_obj["name"]:
        update = True
        ip_obj["name"] = line_name
    if update:
        result = conn.do(
            "update",
            body=ip_obj,
        )
        if result:
            print(result)
        # # **** update host record


if __name__ == "__main__":
    main()
