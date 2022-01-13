#!/usr/bin/env python

"""
import_and_pack_dhcp_reserved_by_mac.py network inputfile [offset]
inputfile format:  IP,MAC,name,fqdn
see help in argparse section
"""


# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging
import re
import json
import itertools
import ipaddress

import bluecat_bam


__progname__ = "import_and_pack_dhcp_reserved_by_mac"
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


def parse_file(inputfile):
    """read the input file"""
    # ip,mac,name,fqdn,other...
    # only ip is required
    # delimiter can be comma, tab, or space
    # "other..." fields are ignored
    line_pat = re.compile(r"((?:\d{1,3}\.){3}\d{1,3})($| |\t|,)")
    ip_import_dict = {}
    mac_import_dict = {}
    with open(inputfile) as f:
        for line in f:
            line = line.strip()

            # get import file info
            line_d = parse_line(line, line_pat)
            if not line_d:
                continue
            ip_import_dict[ipaddress.ip_address(line_d["ip"])] = line_d
            mac = line_d["mac"]
            if mac:
                mac_import_dict[canonical_mac(mac)] = line_d
    return ip_import_dict, mac_import_dict


def set_name(conn, ip_obj, name):
    """set name"""
    if name:
        ip_obj["name"] = name
        result = conn.do("update", method="put", data=ip_obj)
        if result:
            print(result)
        ip_obj = conn.do("getEntityById", method="get", id=ip_obj["id"])
    return ip_obj


def do_checkonly(counts, line_d, ip_obj, obj_mac, obj_state):
    """checkonly mode"""
    logger = logging.getLogger()
    line_mac = canonical_mac(line_d["mac"])
    logger.info(
        "line_mac %s, ip_obj %s, obj_state %s", line_mac, json.dumps(ip_obj), obj_state
    )
    if not ip_obj:
        print("not in BlueCat", line_d)
        counts["importonly"] += 1
    elif not line_mac:
        print("no mac in import", line_d)
        counts["importnomac"] += 1
    elif obj_state in ("DHCP_ALLOCATED", "DHCP_RESERVED"):
        if obj_mac and line_mac == obj_mac:
            print("MAC Address matches", line_d)
            counts["macsame"] += 1
        else:
            print("MAC Address different", line_d)
            counts["macdiff"] += 1
    else:
        print("free in BlueCat", line_d)
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
    logger = logging.getLogger()
    if isinstance(mac, str):
        cmac = "".join([c.lower() for c in mac if c in "0123456789abcdefABCDEF"])
    else:
        cmac = mac
        logger.info("failed to canonicalize mac %s", mac)
    return cmac


def get_args():
    """set up and run config parser"""
    config = bluecat_bam.BAM.argparsecommon(
        "Create DHCP Reserved from imported list, matching by MAC Address, packed without gaps"
    )
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
        "offset",
        default=0,
        help="optional: start IP as offset from start of network, "
        + "or negative for offset from end of network and fill backwards, "
        + "defaults to start of first DHCP range",
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
    return args


def get_my_network(conn, object_ident, configuration_id):
    """get network obj"""
    logger = logging.getLogger()
    network_list = conn.get_obj_list(object_ident, configuration_id, "")
    logger.info("network_list: %s", json.dumps(network_list))
    if len(network_list) > 1:
        print("ERROR - cannot handle more than one network", file=sys.stderr)
        raise ValueError
    network_obj = network_list[0]
    logger.info(network_obj)
    return network_obj


def main():
    """import_and_pack_dhcp_reserved.py"""
    args = get_args()
    offset = int(args.offset)

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, view_id) = conn.get_config_and_view(
            args.configuration, args.view
        )

        # get network
        # {'id': 10602989, 'name': 'VLAN-OTHER', 'type': 'IP4Network', 'properties':
        # {'CIDR': '10.30.2.160/28', 'allowDuplicateHost': 'disable',
        # 'inheritAllowDuplicateHost': 'true', 'pingBeforeAssign': 'disable',
        # 'inheritPingBeforeAssign': 'true', 'gateway': '10.30.2.161',
        # 'inheritDefaultDomains': 'true', 'defaultView': '1048598',
        # 'inheritDefaultView': 'true', 'inheritDNSRestrictions': 'true'}}
        network_obj = get_my_network(conn, args.object_ident, configuration_id)
        networkid = network_obj["id"]
        network = ipaddress.ip_network(network_obj["properties"]["CIDR"])

        # get DHCP range(s)
        # {"id": 8869275, "name": null, "type": "DHCP4Range", "properties":
        # {"start": "10.213.135.5", "end": "10.213.135.254"}}
        range_list = conn.get_dhcp_ranges(network_obj["id"])
        range_info_list = conn.make_dhcp_ranges_list(range_list)

        # get IP info from BAM
        # {"id": 17396816, "name": "MYPC-1450", "type": "IP4Address",
        # "properties": {"address": "10.0.1.244", "state":
        # "DHCP_RESERVED", "macAddress": "DE-AD-BE-EF-16-E8"}}
        # # ip_obj = {"name": "", "properties": {"address":"","state":
        # "", "macAddress": ""}}
        ip_list = get_ip_list(networkid, conn)
        # logger.info(ip_list)
        ip_dict = {
            ipaddress.ip_address(ip_obj["properties"]["address"]): ip_obj
            for ip_obj in ip_list
        }
        # logger.info(ip_dict)
        logger.info(sorted(ip_dict.keys()))

        # read the input file
        # ip,mac,name,fqdn,other...
        # only ip is required
        # delimiter can be comma, tab, or space
        # "other..." fields are ignored
        ip_import_dict, mac_import_dict = parse_file(args.inputfile)
        logger.debug(ip_import_dict)

        # decide on first and last IP, and step direction
        step = 1
        if offset < 0:
            # offset from end on network
            step = -1
            first_ip = network.broadcast_address + offset
            last_ip = network.network_address + 2  # or more?
        elif offset == 0:
            first_ip = range_info_list[0]["start"]
            last_ip = network.broadcast_address - 1
        else:
            first_ip = network.network_address + offset
            last_ip = network.broadcast_address - 1
        # logger.info(first_ip)
        # logger.info(step)
        # logger.info(last_ip)
        walk_subnet(
            first_ip,
            step,
            last_ip,
            ip_dict,
            mac_import_dict,
            conn,
            args,
            configuration_id,
            view_id,
        )


def walk_subnet(
    first_ip,
    step,
    last_ip,
    ip_dict,
    mac_import_dict,
    conn,
    args,
    configuration_id,
    view_id,
):
    """walk through each IP, first pass, replace active IP's with matching MAC Address"""
    # IP address in import data is ignored
    logger = logging.getLogger()
    current_ip = first_ip
    needed = len(mac_import_dict)
    later_ip_list = []
    while current_ip != last_ip and needed > 0:
        logger.info("current %s", current_ip)
        ip_obj = ip_dict.get(current_ip)
        if ip_obj:
            # Need to check state first *****
            # can have multiple IP's with the same mac address,
            # but only the active one 'counts'
            state = ip_obj["properties"]["state"]
            if state in ("DHCP_RESERVED", "DHCP_ALLOCATED", "RESERVED"):
                mac = ip_obj["properties"].get("macAddress")
                if mac:
                    line_d = mac_import_dict.pop(canonical_mac(mac), None)
                    if line_d:
                        # found matching MAC address in import data
                        print("keep %s at %s" % (current_ip, current_ip))
                        match_to_existing(
                            current_ip,
                            line_d,
                            ip_obj,
                            conn,
                            args.checkonly,
                            configuration_id,
                            view_id,
                            args,
                        )
                        needed -= 1
                    else:  # no matching mac in import data
                        if state == "DHCP_ALLOCATED":
                            print(
                                "active but not in import, convert to DHCP Reserved",
                                current_ip,
                            )
                            new_ip_obj = update_dhcp_allocated(conn, ip_obj, mac, None)
                            print(new_ip_obj)
                            # leave any name or hostname unchanged
                        else:
                            print("skip", current_ip, ip_obj)
                else:
                    # no mac address, must be RESERVED, skip it
                    print("skip", current_ip, ip_obj)
            else:
                # state is STATIC or DHCP_FREE, both are 'free' to use
                needed -= 1
                print("use later", current_ip)
                later_ip_list.append(current_ip)
        else:
            # no IP obj, free to use
            needed -= 1
            print("use later", current_ip)
            later_ip_list.append(current_ip)
        current_ip += step
    logger.warning("remaining in mac_import_dict: %s", sorted(mac_import_dict.keys()))

    second_walk(
        conn, mac_import_dict, later_ip_list, ip_dict, args, configuration_id, view_id
    )


def second_walk(
    conn, mac_import_dict, later_ip_list, ip_dict, args, configuration_id, view_id
):
    """walk ip's a second time, filling in"""
    # now walk through the later list and fill in,
    # delete the old IP when moving device
    index = 0
    for mac, line_d in mac_import_dict.items():
        print("mac, line_d", mac, line_d)
        current_ip = later_ip_list[index]
        from_ip = ipaddress.ip_address(line_d["ip"])
        print("move %s to %s" % (from_ip, current_ip))
        ip_obj = ip_dict.get(current_ip)
        print("index, current_ip, ip_obj", current_ip, ip_obj)
        # delete old
        old_obj = ip_dict.get(from_ip)
        if old_obj:
            print("delete", old_obj)
            result = conn.delete_ip_obj(old_obj)
            if result:
                print("deleting old IP result:", result)
        match_to_existing(
            current_ip,
            line_d,
            ip_obj,
            conn,
            args.checkonly,
            configuration_id,
            view_id,
            args,
        )
        index += 1


def match_to_existing(
    current_ip, line_d, ip_obj, conn, checkonly, configuration_id, view_id, args
):
    """compare import and existing data, then add or update"""
    logger = logging.getLogger()

    line_mac = canonical_mac(line_d["mac"])

    # match import info to BlueCat info
    if not ip_obj:
        obj_mac = None
        obj_state = None
        logger.info("ip %s not found in ip_dict", current_ip)
    else:
        obj_mac = canonical_mac(ip_obj["properties"].get("macAddress"))
        obj_state = ip_obj["properties"].get("state")
        logger.info(
            "found ip %s in ip_dict, mac %s, state %s",
            current_ip,
            obj_mac,
            obj_state,
        )

    counts = {
        "importonly": 0,
        "importnomac": 0,
        "macdiff": 0,
        "macsame": 0,
        "dhcpfree": 0,
    }

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

    if checkonly:
        do_checkonly(counts, line_d, ip_obj, obj_mac, obj_state)
        # continue

    # not in checkonly node, take action
    do_action(
        conn,
        current_ip,
        ip_obj,
        line_d,
        line_mac,
        obj_state,
        configuration_id,
        view_id,
        args,
    )


def do_action(
    conn,
    current_ip,
    ip_obj,
    line_d,
    line_mac,
    obj_state,
    configuration_id,
    view_id,
    args,
):
    """update or add dhcp reserved"""
    logger = logging.getLogger()
    if not ip_obj:
        logger.info("not found in range, so create new")

        if not line_mac:
            print("no MAC Address in BlueCat or input line:", line_d)
            return

        ip_obj = make_dhcp_reserved(
            conn,
            str(current_ip),
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
            ip_obj = update_dhcp_allocated(conn, ip_obj, line_mac, line_d["name"])

        elif obj_state == "DHCP_FREE":
            replace_dhcp_free(
                conn,
                ip_obj,
                str(current_ip),
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
    do_fqdn(conn, current_ip, line_d["fqdn"], view_id, line_d)

    final_ip_obj = conn.do("getEntityById", id=ip_obj["id"])
    print(final_ip_obj)


def do_fqdn(conn, current_ip, line_fqdn, view_id, line_d):
    """check or create host record"""
    logger = logging.getLogger()
    if line_fqdn:
        fqdn_objs = conn.get_fqdn(line_fqdn, view_id)
        if fqdn_objs:
            if len(fqdn_objs) > 1:
                print(
                    "error, more than one fqdn found, please fix by hand",
                    line_d,
                )
            else:
                logger.info(fqdn_objs)
                fqdn = fqdn_objs[0]
                fqdn_id = fqdn["id"]
                if current_ip != fqdn["properties"]["addresses"]:
                    fqdn["properties"]["addresses"] = str(current_ip)
                    result = conn.do("update", body=fqdn)
                    if result:
                        print("host record update result: ", result)
                    # print("updated", json.dumps(fqdn))
        else:
            fqdn_id = conn.do(
                "addHostRecord",
                absoluteName=line_fqdn,
                addresses=current_ip,
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


def update_dhcp_allocated(conn, ip_obj, mac, name):
    """update dhcp allocated"""
    logger = logging.getLogger()
    result = conn.do(
        "changeStateIP4Address",
        addressId=ip_obj["id"],
        macAddress=mac,
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
    if name:
        new_ip_obj = set_name(conn, ip_obj, name)
    return new_ip_obj


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
