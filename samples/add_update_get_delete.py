#!/usr/bin/env python

"""add-update-get-delete.py"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


# test data
mac_address = "02-00-02-00-02-00"  # in the user defined range


config = argparse.ArgumentParser(description="add next dhcp reserved")
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
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.loglevel)


with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

    configuration_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=0,
        name=args.configuration,
        type="Configuration",
    )

    config_id = configuration_obj["id"]

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

    print("add new mac address, response is the id of the new entity")
    mac_id = conn.do(
        "addMACAddress",
        method="post",
        configurationId=config_id,
        macAddress=mac_address,
        properties="",
    )
    print("new id is: ", mac_id)
    print()

    print("get mac address just added")
    entity = conn.do(
        "getMACAddress", method="get", configurationId=config_id, macAddress=mac_address
    )
    print(json.dumps(entity))
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

    print("delete mac address, expect null response")
    resp = conn.do("delete", method="delete", objectId=mac_id)
    print(json.dumps(resp))
    print()

    print("check if mac address exists, should get id=0")
    entity = conn.do(
        "getMACAddress", method="get", configurationId=config_id, macAddress=mac_address
    )
    print(json.dumps(entity))
    print()

    # logout is automatic with context manager
    print("done")
