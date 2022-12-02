#!/usr/bin/env python

"""add_DHCP_Reserved.py [--server servername] -f <filename>
OR
add_DHCP_Reserved.py --ip IP --mac MAC --ipname DESC --hostname NAME
(other options available)
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="add DHCP Reserved")
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
config.add_argument("--view", help="BlueCat View", default=os.getenv("BLUECAT_VIEW"))
config.add_argument(
    "--file",
    "--filename",
    "-f",
    help="filename (--file OR --ip and --mac can be used, but not both)",
)
config.add_argument("--ip", "-i", "-a", "--address", help="ip address")
config.add_argument(
    "--mac", "-m", "--hw", "--hardware", help="Interface MAC or HW address"
)
config.add_argument("--ipname", help="optional - name for the IP object")
config.add_argument(
    "--host", "--hostname", "--fqdn", "--dns", "-d", help="optional - hostname"
)
config.add_argument(
    "--logging",
    "-l",
    help="log level, default WARNING (30),"
    + "caution: level DEBUG(10) or less will show the password in the login call",
    default=os.getenv("BLUECAT_LOGGING", "WARNING"),
)
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.loglevel)

configuration_name = args.configuration
view_name = args.view
filename = args.file
ip = args.ip
mac = args.mac
ipname = args.ipname
hostname = args.host

if not (configuration_name and view_name):
    print("--config and --view must be  defined")
    config.print_help()
    sys.exit(1)
if filename:
    if ip or mac:
        print("--file cannot be used with --ip and --mac, use one or other")
        config.print_help()
        sys.exit(1)
    else:
        # read file here ****
        print("code to read file not completed")
        # ????
elif not (ip and mac):
    print("either --file OR both ( --ip and --mac ) must be specified")
    config.print_help()
    sys.exit(1)

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
        name=view_name,
        type="View",
    )
    view_id = view_obj["id"]

    """
    network_obj = conn.do(
        "getIPRangedByIP",
        method="get",
        containerId=configuration_id,
        type="IP4Network",
        address=ip,
    )
    network_id = network_obj["id"]
    """

    if hostname:
        hostinfo_list = [
            hostname,
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
    new_ip_obj = conn.do("getEntityById", id=new_ip_id)
    # print(json.dumps(new_ip_obj))
    newid = new_ip_obj["id"]

    # cannot set object name in previous call, so update it with the name
    # use hostname for the object name
    if ipname:
        new_ip_obj["name"] = ipname
        updated_ip_obj = conn.do("update", method="put", data=new_ip_obj)
        new_ip_obj = conn.do("getEntityById", method="get", id=newid)
    print(json.dumps(new_ip_obj))
