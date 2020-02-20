#!/usr/bin/env python

"""add_update_get_delete_requests.py
using only requests package, for testing and comparision"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import requests


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
logger.setLevel(args.logging)

mainurl = "https://" + args.server + "/Services/REST/v1/"
conn = requests.Session()
resp = conn.get(
    mainurl + "login?", params={"username": args.username, "password": args.password}
)
token = resp.json()
token = token.split()[2] + " " + token.split()[3]
conn.headers.update({"Authorization": token, "Content-Type": "application/json"})

resp = conn.request(
    url=mainurl + "getEntityByName" + "?",
    method="get",
    params={"parentId": 0, "name": args.configuration, "type": "Configuration"},
)
configuration_obj = resp.json()
# print(json.dumps(configuration_obj))

config_id = configuration_obj["id"]
print("config_id: {}".format(config_id))

print("check if mac address exists, should get id=0 if not")
resp = conn.request(
    url=mainurl + "getMACAddress" + "?",
    method="get",
    params={"configurationId": config_id, "macAddress": mac_address},
)
oldmac = resp.json()

print("old mac is: ", json.dumps(oldmac))
mac_id = oldmac["id"]
print("id: ", mac_id)
if mac_id != 0:
    print("ERROR - mac address already exists")
    sys.exit(1)
print()

print("add new mac address, response is the id of the new entity")
resp = conn.request(
    url=mainurl + "addMACAddress" + "?",
    method="post",
    params={"configurationId": config_id, "macAddress": mac_address, "properties": ""},
)
mac_id = resp.json()
print("new id is: ", mac_id)
print()

print("get mac address just added")
resp = conn.request(
    url=mainurl + "getMACAddress" + "?",
    method="get",
    params={"configurationId": config_id, "macAddress": mac_address},
)
entity = resp.json()
print(json.dumps(entity))
print()

print("change name in local copy of the mac address")
entity["name"] = "testmac"
print(json.dumps(entity))
print()

print("update the mac address in bluecat, expect null response")
resp = conn.request(
    url=mainurl + "update" + "?",
    method="put",
    json=entity,
)
print(resp)
print()

print("get mac address from bluecat")
resp = conn.request(
    url=mainurl + "getMACAddress" + "?",
    method="get",
    params={"configurationId": config_id, "macAddress": mac_address},
)
entity = resp.json()
print(json.dumps(entity))
print()

print("delete mac address, expect null response")
resp = conn.request(
    url=mainurl + "delete" + "?", method="delete", params={"objectId": mac_id}
)
print(resp)
print()

print("check if mac address exists, should get id=0")
resp = conn.request(
    url=mainurl + "getMACAddress" + "?",
    method="get",
    params={"configurationId": config_id, "macAddress": mac_address},
)
entity = resp.json()
print(json.dumps(entity))
print()

print("logout")
resp = conn.request(url=mainurl + "logout" + "?", method="get")
print("done")
