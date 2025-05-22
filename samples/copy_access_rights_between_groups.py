#!/usr/bin/env python

"""copy_access_rights_between_groups.py
copy access rights from one group to another"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(
    description="copy access rights from one group to another"
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
config.add_argument("from_group", help="group name or user name")
config.add_argument("to_group", help="group name or user name")
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
from_group = args.from_group
to_group = args.to_group

# all these must be specified (or defaulted)
if not (configuration_name and from_group and to_group):
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

    from_group_obj = conn.do(
        "getEntityByName", method="get", parentId=0, name=from_group, type="UserGroup"
    )
    from_group_id = from_group_obj["id"]

    if from_group_id == 0:
        print("error finding from_group %s" % (from_group))
        sys.exit(1)

    to_group_obj = conn.do(
        "getEntityByName", method="get", parentId=0, name=to_group, type="UserGroup"
    )
    to_group_id = to_group_obj["id"]

    if to_group_id == 0:
        print("error finding to_group %s" % (to_group))
        sys.exit(1)

    # get access rights from from_group
    accessrights = conn.do(
        "getAccessRightsForUser", userId=from_group_id, start=0, count=99999
    )

    # get existing access rights to look for conflicts
    existing = conn.do(
        "getAccessRightsForUser", userId=to_group_id, start=0, count=99999
    )
    existing_by_id = {right["entityId"]: right for right in existing}

    # add access rights to to_group
    for accessright in accessrights:
        if existing_by_id.get(accessright["entityId"]):
            print("access right conflict")
            print("existing: %s" % (existing_by_id[accessright["entityId"]]))
            print("new: %s" % (accessright))
        else:
            print("add access right: %s" % (accessright))
            accessrightid = conn.do(
                "addAccessRight",
                entityId=accessright["entityId"],
                userId=to_group_id,
                value=accessright["value"],
                overrides=accessright["overrides"],
                properties=accessright["properties"],
            )
