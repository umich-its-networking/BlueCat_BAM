#!/usr/bin/env python

"""add_mac_to_pool.py mac-address "mac-pool-name"
"""

# to be python2/3 compatible:
from __future__ import print_function

import datetime
import os
import sys
import json
import argparse
import logging

import bluecat_bam

def main():
    """add mac to pool"""
    config = argparse.ArgumentParser(description="Add MAC Address to MAC Pool, if not already in a pool")
    config.add_argument("mac", help="MAC Address")
    config.add_argument("pool", help="MAC Pool")
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
        "--loglevel",
        "--logging",
        "-l",
        help="log level, default WARNING (30),"
        + "caution: level DEBUG(10) or less will show the password in the login call",
        default=os.getenv("BLUECAT_LOGGING", "WARNING"),
    )
    config.add_argument(
        "--force",
        "-f",
        help="If already in a different MAC Pool, remove from that pool and put in new pool",
        action="store_true",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    configuration_name = args.configuration
    mac = args.mac
    pool = args.pool
    force = args.force

    if not (configuration_name and mac):
        config.print_help()
        sys.exit(1)

    conn = bluecat_bam.BAM(args.server, args.username, args.password)

    configuration_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=0,
        name=configuration_name,
        type="Configuration",
    )

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration, args.view)
        add_mac_to_pool(mac,pool, configuration_id, conn, force, username=args.username)


def add_mac_to_pool(mac, pool, configuration_id, conn, force, username=None):
    '''add_mac_to_pool'''

    pool_obj = conn.do(
        "getEntityByName", parentId=configuration_id, name=pool, type="MACPool"
    )
    pool_id = pool_obj["id"]

    # print(json.dumps(pool_obj))
    if pool_id == 0:
        print("pool '%s' not found" % (pool))
        sys.exit(3)


    mac_obj = conn.do(
        "getMACAddress", method="get", configurationId=configuration_id, macAddress=mac
    )
    mac_id = mac_obj["id"]
    # print(json.dumps(mac_obj))
    if mac_id == 0:  # MAC Address object does not exist yet
        mac_id = conn.do(
            "addMACAddress",
            method="post",
            configurationId=configuration_id,
            macAddress=mac,
            properties="",
        )
        if mac_id == 0:
            print("failed to create mac address object")
            sys.exit(1)
        mac_obj = conn.do(
            "getMACAddress", method="get", configurationId=configuration_id, macAddress=mac
        )
    else:  # MAC Address object already exists
        old_pool = mac_obj["properties"].get("macPool")
        if old_pool:
            if old_pool != pool:
                if force:
                    print("removing from old pool '%s'" % (old_pool))
                else:
                    print("MAC is in pool '%s', add --force to override" % (old_pool))
                    sys.exit()
            else:
                print("already in that pool")
                sys.exit()

    # print("ok")


    try:
        conn.do(
            "associateMACAddressWithPool",
            configurationId=configuration_id,
            macAddress=mac,
            poolId=pool_id,
        )
    except ValueError:
        print("value error trying to put mac in pool")

    # add username in the "registered by" field
    if username:
        mac_obj['properties']['reg_by']=username
    # add 'registration date'
    d=str(datetime.datetime.now(datetime.timezone.utc))[:19]
    mac_obj['properties']['reg_date']=d
    # update MAC addres
    result=conn.do("update",body=mac_obj)
    if result:
        print("Attempted to update requestor and date:",result)

    mac_obj = conn.do(
        "getMACAddress", method="get", configurationId=configuration_id, macAddress=mac
    )
    print(json.dumps(mac_obj))

if __name__ == "__main__":
    main()
