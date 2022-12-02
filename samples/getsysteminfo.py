#!/usr/bin/env python

"""getSystemInfo.py"""

# to be python2/3 compatible:
from __future__ import print_function

import json

import bluecat_bam

config = bluecat_bam.BAM.argparsecommon()
args = config.parse_args()

"""
logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.loglevel)
"""

opts = {"timeout": None, "max_retries": 0}

# with bluecat_bam.BAM(args.server, args.username, args.password, **opts) as conn:
with bluecat_bam.BAM(**vars(args), **opts) as conn:
    info = conn.do("getSystemInfo", method="get")
    print(json.dumps(info))
