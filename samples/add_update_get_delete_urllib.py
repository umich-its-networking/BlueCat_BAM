#!/usr/bin/env python

"""add_update_get_delete_urllib.py
using only urllib package, for testing and comparision"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import urllib.request

from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request


def main():
    """add_update_get_delete"""
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

    mainurl = "https://" + args.server + "/Services/REST/v1/"

    add_update_get_delete(mainurl, args, mac_address)


def make_request(url, headers=None, data=None, method=None, params=None):
    """request similar to requests"""
    # print("url %s params %s" % (url, params))
    if params:
        params = urllib.parse.urlencode(params)
        url = "%s%s" % (url, params)
    request = Request(url, headers=headers or {}, data=data, method=method)
    try:
        # bandit blacklists urlopen because it can open files also
        # that is not a concern here
        with urlopen(request, timeout=10) as response:  # nosec
            if response.status != 200:
                print(response.status)
            return response.read(), response
    except HTTPError as error:
        print(error.status, error.reason)
    except URLError as error:
        print(error.reason)
    except TimeoutError:
        print("Request timed out")
    return None, None


def add_update_get_delete(mainurl, args, mac_address):
    """add_update_get_delete"""
    params = {"username": args.username, "password": args.password}
    body, _ = make_request(mainurl + "login?", params=params)
    token = body.split()[2] + b" " + body.split()[3]
    # print(token)

    headers = {"Authorization": token, "Content-Type": "application/json"}

    params = {"parentId": 0, "name": args.configuration, "type": "Configuration"}
    # print(params)
    body, _ = make_request(mainurl + "getEntityByName?", params=params, headers=headers)
    configuration_obj = json.loads(body)
    # print(configuration_obj)

    config_id = configuration_obj["id"]
    print("config_id: {}".format(config_id))

    print("check if mac address exists, should get id=0 if not")
    resp, _ = make_request(
        url=mainurl + "getMACAddress" + "?",
        method="get",
        params={"configurationId": config_id, "macAddress": mac_address},
        headers=headers,
    )
    oldmac = json.loads(resp)

    print("old mac is: ", json.dumps(oldmac))
    mac_id = oldmac["id"]
    print("id: ", mac_id, "\n")
    if mac_id != 0:
        print("ERROR - mac address already exists")
        sys.exit(1)

    print("add new mac address, response is the id of the new entity")
    resp, _ = make_request(
        url=mainurl + "addMACAddress" + "?",
        method="post",
        params={
            "configurationId": config_id,
            "macAddress": mac_address,
            "properties": "",
        },
        headers=headers,
    )
    mac_id = json.loads(resp)
    print("new id is: ", mac_id, "\n")

    print("get mac address just added")
    resp, _ = make_request(
        url=mainurl + "getMACAddress" + "?",
        method="get",
        params={"configurationId": config_id, "macAddress": mac_address},
        headers=headers,
    )
    entity = json.loads(resp)
    print(json.dumps(entity), "\n")

    print("change name in local copy of the mac address")
    entity["name"] = "testmac"
    print(json.dumps(entity), "\n")

    print("update the mac address in bluecat, expect null response")
    json_string = json.dumps(entity)
    post_data = json_string.encode("utf-8")
    resp, _ = make_request(
        url=mainurl + "update" + "?", method="put", data=post_data, headers=headers
    )
    print(resp.decode("utf-8"), "\n")

    print("get mac address from bluecat")
    resp, _ = make_request(
        url=mainurl + "getMACAddress" + "?",
        method="get",
        params={"configurationId": config_id, "macAddress": mac_address},
        headers=headers,
    )
    entity = json.loads(resp)
    print(json.dumps(entity), "\n")

    print("delete mac address, expect null response")
    resp, _ = make_request(
        url=mainurl + "delete" + "?",
        method="delete",
        params={"objectId": mac_id},
        headers=headers,
    )
    print(resp.decode("utf-8"), "\n")

    print("check if mac address exists, should get id=0")
    resp, _ = make_request(
        url=mainurl + "getMACAddress" + "?",
        method="get",
        params={"configurationId": config_id, "macAddress": mac_address},
        headers=headers,
    )
    entity = json.loads(resp)
    print(json.dumps(entity), "\n")

    print("logout")
    resp, _ = make_request(url=mainurl + "logout" + "?", method="get", headers=headers)
    print("done")


if __name__ == "__main__":
    main()
