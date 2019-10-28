#!/usr/bin/env python

"""add_TXT_record.py viewId absoluteName txt ttl properties"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="add TX Record")
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
# arguments: viewId absoluteName txt ttl properties
config.add_argument("viewId")
config.add_argument("absoluteName", help="DNS FQDN")
config.add_argument("txt", help="TXT data")
config.add_argument("ttl", help="TTL, use -1 for zone default")
config.add_argument("properties", help="properties, in 'name=value|..' format")
config.add_argument(
    "--logging",
    "-l",
    help="log level, default WARNING (30),"
    + "caution: level DEBUG(10) or lower will show the password in the login call",
    default=os.getenv("BLUECAT_LOGGING", "WARNING"),
)
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.logging)

if not (args.viewId and args.absoluteName and args.txt and args.ttl):
    config.print_help()
    sys.exit(1)

with bluecat_bam.BAM(args.server, args.username, args.password, raw_in=True) as conn:

    obj_id = conn.do(
        "addTXTRecord",
        viewId=args.viewId,
        absoluteName=args.absoluteName,
        txt=args.txt,
        ttl=args.ttl,
        properties=args.properties,
    )
    print(json.dumps(obj_id))

    new_obj = conn.do("getEntityById", method="get", id=obj_id)
    print(json.dumps(new_obj))
