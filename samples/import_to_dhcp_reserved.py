#!/usr/bin/env python

"""
import_to_dhcp_reserved.py < output-from-arubaIntermapperSnmp
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging
import re
import json

import bluecat_bam


__progname__ = "import_to_dhcp_reserved"
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


def get_ip_list(networkid, conn):
    """get list of IP objects"""
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
    return ip_list


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


def set_name(conn, obj, name):
    if name:
        ip_obj["name"] = name
        updated_ip_obj = conn.do("update", method="put", data=new_ip_obj)
        ip_obj = conn.do("getEntityById", method="get", id=newid)
    return ip_obj


def make_dhcp_reserved(conn, ip,mac,name, fqdn, configuration_id, view_id):
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
    # print(json.dumps(ip_obj))
    ##newid = ip_obj["id"]
    # cannot set object name in previous call, so update it with the name
    if name:
        ip_obj = set_name(conn, obj, name)
    #print(json.dumps(ip_obj))
    return ip_obj


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
        + " Extra fields will be ignored.  ipname cannot have spaces."
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    object_ident = args.object_ident
    rangetype = ""
    inputfile = args.inputfile

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        view_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=configuration_id,
            name=args.view,
            type="View",
        )
        view_id = view_obj["id"]

        obj_list = conn.get_obj_list(conn, object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        ip_dict={}
        for entity in obj_list:
            entityId = entity["id"]
            matching_list = get_ip_list(entityId, conn)
            for ip in matching_list:
                ip_address = ip["properties"]["address"]
                ip_dict[ip_address] = ip

        # now read the data from csv file from controller
        with open(inputfile) as f:
            line_pat = re.compile(r"((?:\d{1,3}\.){3}\d{1,3})($|[^\d])")
            for line in f:
                line = line.strip()
                if line == "":  # skip blank lines
                    continue
                # match IP Address and the following delimiter
                line_match = line_pat.match(line)
                if not line_match:
                    print("did not find IP and delimiter in line:",line)
                    continue
                delimiter = line_match.group(2)
                if delimiter not in (" ","\t",","):
                    print("delimiter not recognized in:", line)
                    continue
                line_split=line.split(delimiter)
                line_len = len(line_split)
                print(line_split, line_len)
                for i in range(5):
                    print(i)
                    if i >= line_len:
                        line_split.append("")
                    elif not line_split[i]:
                        line_split[i] = ""
                # print("ip",line_split[0],"mac",line_split[1],"name",line_split[2],"dns",line_split[3],"other",line_split[4])
                (line_ip,line_mac,line_name,line_fqdn,other)=line_split[0:5]
                print("ip",line_ip,"mac",line_mac,"name",line_name,"dns",line_fqdn,"other",other)


                # find in range data
                try:
                    ip_obj = ip_dict[line_ip]
                except KeyError:
                    print("not found in range, so create new")
                    # {"id": 17396816, "name": "MYPC-1450", "type": "IP4Address", "properties": {"address": "10.0.1.244", "state": "DHCP_RESERVED", "macAddress": "DE-AD-BE-EF-16-E8"}}
                    ##ip_obj = {"name": "", "properties": {"address":"","state": "", "macAddress": ""}}
                    ##ip_dict[line_ip]=ip_obj
                    # fill in new values??  no -create new
                    if not line_mac:
                        print("no MAC Address in BlueCat, need more info for:",line)
                        continue

                    ip_obj=make_dhcp_reserved(conn, ip,mac,name, fqdn, configuration_id, view_id)
                    continue    # created new DHCP_RESERVED

                # convert and update existing IP
                # first get mac address object
                print(json.dumps(line_mac))
                if line_mac:
                    # check if mac object exists in bam
                    mac_obj = conn.do("getMACAddress", method="get", configurationId=configuration_id, macAddress=line_mac)
                    '''
                    if mac_obj["id"] == 0:
                        # create new MAC object
                        mac_id = conn.do(
                            "addMACAddress",
                            method="post",
                            configurationId=configuration_id,
                            macAddress=mac,
                            properties="",
                        )
                        # mac_obj = conn.do("getMACAddress", method="get", configurationId=configuration_id, macAddress=mac)
                    '''
                else:   # no mac in import data, find in bam
                    line_mac = ip_obj['properties'].get('macAddress')
                    if not line_mac:
                        print("error - no MAC Address in IP or import")
                        continue
                old_state = ip_obj['properties']['state']
                if old_state == "DHCP_ALLOCATED" or old_state == "STATIC":
                    result = conn.do(
                        "changeStateIP4Address",
                        addressId=ip_obj["id"],
                        macAddress=line_mac,
                        targetState="MAKE_DHCP_RESERVED",
                    )
                    if result:
                        print("changestate result:",result)
                    new_ip_obj = conn.do(
                        "getEntityById",
                        id=ip_obj["id"],
                    )
                    print("new",new_ip_obj)
                    ip_obj = new_ip_obj

                    # update the name (cannot be done in the above API)
                    if line_name:
                        updated_ip_obj = set_name(conn, ip_obj, line_name)
                elif old_state == "DHCP_FREE":
                    # cannot convert directly to reserved, delete, and recreate
                    result = conn.do(
                        "delete",
                        objectId=ip_obj["id"],
                    )
                    if result:
                        print("deleting DHCP_FREE result:",result)
                    ip_obj=make_dhcp_reserved(conn, line_ip,line_mac,line_name,line_fqdn, configuration_id, view_id)
                    print("replaced with:",ip_obj)
                elif old_state == "DHCP_RESERVED":
                    update=False
                    if ip_obj['properties']['macAddress'] != line_mac:
                        update = True
                        ip_obj['properties']['macAddress'] = line_mac
                    if line_name and line_name != ip_obj['name']:
                        update = True
                        ip_obj['name'] = line_name
                    if update:
                        result = conn.do(
                            "update",
                            body=ip_obj,
                        )
                        if result:
                            print(result)
                        ## **** update host record

                else:
                    print("error - cannot handle state:",old_state)

        final_ip_obj=conn.do(
            "getEntityById",
            id=ip_obj['id']
        )
        print(final_ip_obj)
    return


if __name__ == "__main__":
    main()
