#!/usr/bin/env python

"""add_user.py username first last"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import json
import argparse
import logging

import bluecat_bam


# ###### PRESET CONSTANTS - EDIT FOR YOUR USE ######
# preset constants (edit for your use)
authenticator_id = 9115247  # should look up authenticator, but this is faster
password = "this_password_is_not_used"  # nosec  - dummy password required,
#                                       but not used by authenticator
# ###### there are other assumptions in this code - review before using ######

config = argparse.ArgumentParser(description="BlueCat Address Manager add user")
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
config.add_argument("newusername")
config.add_argument("newfirstname")
config.add_argument("newlastname")
config.add_argument("newemail")
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

conn = bluecat_bam.BAM(args.server, args.username, args.password)

user_obj_id = conn.do(
    "addUser",
    method="post",
    username=args.newusername,
    password=password,
    properties={
        "email": args.newemail,
        "firstname": args.newfirstname,
        "lastname": args.newlastname,
        "authenticator": authenticator_id,
        "userType": "REGULAR",
        "securityPrivilege": "VIEW_OTHERS_ACCESS_RIGHTS",  # our default
        "userAccessType": "GUI",
        "historyPrivilege": "VIEW_HISTORY_LIST",  # our default
    },
)

user_obj = conn.do("getEntityById", method="get", id=user_obj_id)

print(json.dumps(user_obj))

conn.logout()
