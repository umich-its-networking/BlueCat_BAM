#!/usr/bin/env python

"""update_fqdn_special.py config view type domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import json
import logging

import bluecat_bam


config = bluecat_bam.BAM.argparsecommon(
    "restore data on prod from a test server, not for normal use"
)
config.add_argument("--type", help="DNS record type", default="HostRecord")
config.add_argument(
    "--host", "--hostname", "--fqdn", "--dns", "-d", help="DNS domain name or hostname"
)
args = config.parse_args()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
logger.setLevel(args.logging)

configuration_name = args.configuration
view_name = args.view
record_type = args.type
domain_name = args.host

if not (configuration_name and view_name):
    config.print_help()
    sys.exit(1)

with bluecat_bam.BAM(
    "https://bluecat-test-2.umnet.umich.edu:9999", args.username, args.password
) as conn:

    (configuration_id, view_id) = conn.get_config_and_view(
        configuration_name, view_name
    )

    # open second conn to test server with data to copy
    with bluecat_bam.BAM(
        "https://bluecat-test-2.umnet.umich.edu:6666", args.username, args.password
    ) as conn2:
        (configuration_id2, view_id2) = conn2.get_config_and_view(
            configuration_name, view_name
        )

        for line in sys.stdin:
            domain_name = line.rstrip("\r\n")

            entities = conn.get_fqdn(domain_name, view_id, record_type)

            if len(entities) != 1:
                print("not on prod:", entities, domain_name)
            else:
                entity_curr = entities[0]
                print("current:", json.dumps(entity_curr))

            entities = conn2.get_fqdn(domain_name, view_id, record_type)

            if len(entities) != 1:
                print("not on test:", entities, domain_name)
                continue
            entity_old = entities[0]
            print("old:", json.dumps(entity_old))

            if entity_curr["id"] != entity_old["id"]:
                print("ids do not match, skip:", domain_name)
                continue
            result = conn.do("update", body=entity_old)
            if result:
                print("update result:", result)

            entities = conn.get_fqdn(domain_name, view_id, record_type)

            if len(entities) != 1:
                print("failed update:", entities, domain_name)
                continue
            entity_check = entities[0]
            print("check:", json.dumps(entity_check))
