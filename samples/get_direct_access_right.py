#!/usr/bin/env python

"""get_direct_access_right.py
find access right directly from user or group to entity, not inherited
"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(
    description="find access right directly from user or group to entity, "
    + "not inherited"
)
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
config.add_argument("--owner_id", "-o", help="id of user or group")
config.add_argument("--entity_id", "-e", help="id of entity")
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
owner_id = int(args.owner_id)
entity_id = args.entity_id

# all these must be specified (or defaulted)
if not (configuration_name and view_name and owner_id and entity_id):
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
configuration_id = configuration_obj["id"]
logging.info("configuration id: %s", configuration_id)

view_obj = conn.do(
    "getEntityByName",
    method="get",
    parentId=configuration_id,
    name=view_name,
    type="View",
)
view_id = view_obj["id"]
logging.info("view_id: %s", view_id)

if not (configuration_id and view_id):
    print("error finding Configuration or View")
    sys.exit(1)


# get list of rights, search for specific owner
rights = conn.do(
    "getAccessRightsForEntity", method="get", entityId=entity_id, start=0, count=9999
)
logging.info("rights: %s", rights)
logging.info("owner_id type: %s", type(owner_id))

# search for owner
found_right = None
for right in rights:
    logging.info("right: %s", right)
    right_owner = right["userId"]
    logging.info("right_owner: %s", right_owner)
    logging.info("right_owner type: %s", type(right_owner))
    if right_owner == owner_id:
        logging.info("found: %s", right_owner)
        found_right = right
        break
logging.info("final right_owner: %s", right_owner)
if found_right:
    print(found_right)
else:
    print("direct right not found")

conn.logout()
