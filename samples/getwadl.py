#!/usr/bin/env python

"""getwadl.py"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import argparse
import logging

import bluecat_bam


config = argparse.ArgumentParser(description="get wadl file")
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

opts = {"timeout": None, "max_retries": 0}
with bluecat_bam.BAM(args.server, args.username, args.password, **opts) as conn:
    info = conn.request(
        "GET", "https://" + args.server + "/Services/REST/application.wadl"
    )
    print(info.text)
