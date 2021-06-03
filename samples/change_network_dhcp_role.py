#!/usr/bin/env python

"""change_network_dhcp_role.py"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam

print("NOT WORKING YET")

config = argparse.ArgumentParser(description="change network dhcp role")
config.add_argument(
    "--server",
    "-s",
    # env_var="BLUECAT_SERVER",
    default=os.getenv("BLUECAT_SERVER"),
    help="BlueCat Address Manager hostname",
)
config.add_argument(
    "--username",
    "-u",
    # env_var="BLUECAT_USERNAME",
    default=os.getenv("BLUECAT_USERNAME"),
)
config.add_argument(
    "--password",
    "-p",
    # env_var="BLUECAT_PASSWORD",
    default=os.getenv("BLUECAT_PASSWORD"),
    help="password in environment, should not be on command line",
)
config.add_argument(
    "--configuration",
    "--cfg",
    help="BlueCat Configuration name",
    default=os.getenv("BLUECAT_CONFIGURATION"),
)
config.add_argument(
    "--logging",
    "-l",
    help="log level, default WARNING (30),"
    + "caution: level DEBUG(10) or less will show the password in the login call",
    default=os.getenv("BLUECAT_LOGGING", "WARNING"),
)
config.add_argument("network")
config.add_argument("primary_server")
config.add_argument("secondary_server", default=None)
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

    config_id = configuration_obj["id"]
    print(config_id)

    # parse the networkid
    # should match to pattern for error checking

    (networkip, prefix) = args.network.split("/", 1)
    print(networkip)

    # get networkid

    networkobj = conn.do(
        "getIPRangedByIP", containerId=config_id, type="IP4Network", address=networkip
    )
    print(json.dumps(networkobj))
    networkid = networkobj["id"]
    print(networkid)

    # get dhcp change_network_dhcp_role

    roles = conn.do("getDeploymentRoles", entityId=networkid)
    # print(json.dumps(roles))

    dhcp_role = None
    for role in roles:
        if role["service"] == "DHCP":
            dhcp_role = role
            break

    print(json.dumps(dhcp_role))

    roleid = dhcp_role["id"]
    svr_int_id = dhcp_role["serverInterfaceId"]
    sec_svr_int_id = dhcp_role["properties"]["secondaryServerInterfaceId"]
    print(svr_int_id, sec_svr_int_id)

    # get primary_server

    primary_interfaces = conn.do(
        "searchByObjectTypes",
        keyword="^%s$" % (args.primary_server),
        types="NetworkServerInterface",
        start=0,
        count=999,
    )
    print(json.dumps(primary_interfaces))
    count = len(primary_interfaces)
    print(count)
    if count == 0:
        print("Error - did not find server %s" % (args.primary_server))
        sys.exit(1)
    elif count > 1:
        print("Error - matched more than one server for %s" % (args.primary_server))
        for interface in primary_interfaces:
            print(json.dumps(interface))
        sys.exit(1)
    pri_int_id = primary_interfaces[0]["id"]
    print(pri_int_id)

    # get secondary_server
    secondary_interfaces = conn.do(
        "searchByObjectTypes",
        keyword="^%s$" % (args.secondary_server),
        types="NetworkServerInterface",
        start=0,
        count=999,
    )
    print(json.dumps(secondary_interfaces))
    count = len(secondary_interfaces)
    print(count)
    if count == 0:
        print("Error - did not find server %s" % (args.secondary_interfaces))
        sys.exit(1)
    elif count > 1:
        print(
            "Error - matched more than one server for %s" % (args.secondary_interfaces)
        )
        for interface in secondary_interfaces:
            print(json.dumps(interface))
        sys.exit(1)
    sec_int_id = secondary_interfaces[0]["id"]
    print(sec_int_id)

    # compare new values with old values
    if pri_int_id == svr_int_id and sec_int_id == sec_svr_int_id:
        print("No change")
        sys.exit()
    # print("DHCP role was %s and %s" % ()) # would have to look up old servers

    resp = conn.do("update", body=dhcp_role)

    print("NOT WORKING YET")

    # pylint: disable=W0105
    """ # pylint: disable=W0105
    print("check if mac address exists, should get id=0 if not")
    oldmac = conn.do(
        "getMACAddress", method="get", configurationId=config_id, macAddress=mac_address
    )
    print("old mac is: ", json.dumps(oldmac))
    mac_id = oldmac["id"]
    print("id: ", mac_id)
    if mac_id != 0:
        print("ERROR - mac address already exists")
        sys.exit(1)
    print()




    print("change name in local copy of the mac address")
    entity["name"] = "testmac"
    print(json.dumps(entity))
    print()

    print("update the mac address in bluecat, expect null response")
    resp = conn.do("update", method="put", body=entity)
    print(json.dumps(resp))
    print()

    print("get mac address from bluecat")
    entity = conn.do(
        "getMACAddress", method="get", configurationId=config_id, macAddress=mac_address
    )
    print(json.dumps(entity))
    print()
    """  # pylint: disable=W0105

    print("done")  # logout is automatic with context manager
