#!/usr/bin/env python

"""upload_policy_items.py
using only requests package, for testing and comparision"""

# to be python2/3 compatible:
from __future__ import print_function

import os
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
config.add_argument("policy_id")
config.add_argument("filename")
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
# print(configuration_obj)

config_id = configuration_obj["id"]
print("config_id: {}".format(config_id))


def upload_response_policy_items(my_token, host, parent_id, filename):
    """call BlueCat API uploadResponsePolicyItems"""
    url = "http://{0}/Services/REST/v1/uploadResponsePolicyItems".format(host)
    headers = {
        "Authorization": my_token,
    }

    querystring = {"parentId": parent_id}
    files = {"data": open(filename, "rb")}
    my_response = requests.post(url, headers=headers, params=querystring, files=files)
    return my_response.text


response = upload_response_policy_items(
    token, args.server, args.policy_id, args.filename
)

print("response: ", response)


print("check if policy item exists, should get id=0 if not")
resp = conn.request(
    url=mainurl + "searchResponsePolicyItems" + "?",
    method="get",
    params={"scope": "Local", "keyword": "*", "start": 0, "count": 10},
)
items = resp.json()

print("items: ", json.dumps(items))


print("logout")
resp = conn.request(url=mainurl + "logout" + "?", method="get")
print("done")
