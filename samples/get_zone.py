#!/usr/bin/env python

"""get_fqdn.py config view type domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging

import bluecat_bam


config = bluecat_bam.BAM.argparsecommon("Get fully qualified domain name object")
config.add_argument("--type", help="DNS record type", default="HostRecord")
config.add_argument("domain_name", help="DNS domain name or hostname")
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.logging)

configuration_name = args.configuration
view_name = args.view
record_type = args.type
domain_name = args.domain_name

if not (configuration_name and view_name and record_type and domain_name):
    config.print_help()
    sys.exit(1)

with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

    (configuration_id, view_id) = conn.get_config_and_view(
        configuration_name, view_name
    )

    entity, remainder = conn.get_zone(domain_name, view_id)
    print("zone:", json.dumps(entity))
    print("remainder:", remainder)
