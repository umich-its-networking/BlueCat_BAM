#!/usr/bin/env python

"""update_property_by_id.py entityId "name=value"
"""

# example usage:
# while read id; do update_property_by_id.py $id "exp_date=2099-01-01 00:00:00.0";
#   done < ids.20191009

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="Add or update a property")
config.add_argument("entityId")
config.add_argument("newprop", help="new property name=value")
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
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.loglevel)

configuration_name = args.configuration
# view_name = args.view
entity_id = args.entityId
newprop = args.newprop

if not (configuration_name and entity_id and newprop):
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

    """
    view_obj = conn.do(
        "getEntityByName",
        method="get",
        parentId=configuration_id,
        name=view_name,
        type="View",
    )
    view_id = view_obj["id"]
    """

    obj = conn.do("getEntityById", id=entity_id)
    obj_id = obj["id"]

    # print(json.dumps(pool_obj))
    if obj_id == 0:
        print("object '%s' not found" % (entity_id))
        sys.exit(3)

    # parse newprop
    (name, value) = newprop.split("=")
    # print("name: %s, value: %s" % (name,value))

    # print("before:")
    # print(json.dumps(obj))
    obj["properties"][name] = value
    # print("after:")
    print(json.dumps(obj))

    # update database
    return_code = conn.do("update", body=obj)
    if return_code:
        print("return code: %s" % (return_code))

    new_obj = conn.do("getEntityById", id=entity_id)
    new_obj_id = new_obj["id"]

    # print(json.dumps(pool_new_obj))
    if new_obj_id == 0:
        print("new object '%s' not found" % (entity_id))
        sys.exit(3)

    # print("updated:")
    # print(json.dumps(new_obj))
