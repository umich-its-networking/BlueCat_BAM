#!/usr/bin/env python

"""get_admin_users.py"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="get ip by mac address")
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

conn = bluecat_bam.BAM(args.server, args.username, args.password)

user_obj_list = conn.do(
    "searchByObjectTypes",
    method="get",
    keyword="*",
    types="User",
    start=0,
    count=1000,  # assume less than 1000 users
)


for user_obj in user_obj_list:
    if user_obj["properties"]["userType"] == "ADMIN":
        print(json.dumps(user_obj))
