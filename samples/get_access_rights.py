#!/usr/bin/env python

"""get_access_rights.py
add access right for a group to an entity in BlueCat BAM"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import sys
import json
import argparse
import logging
import requests

import bluecat_bam


__progname__ = "get_access_rights"
__version__ = "0.1"


def main():
    """get_access_rights"""
    config = bluecat_bam.BAM.argparsecommon("get_access_rights")
    config.add_argument("entity", help="entity name, IP, CIDR, id, filename, or '-'")
    config.add_argument("--type", help="optional entity type")
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    record_type = args.type

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (configuration_id, view_id) = conn.get_config_and_view(args.configuration, args.view)

        obj_list = conn.get_obj_list(args.entity, view_id, record_type)

        for obj in obj_list:
            get_access_rights(obj,conn)


def get_access_rights(obj,conn):
    logger = logging.getLogger()

    print(json.dumps(obj))

    access_list = conn.get_obj_list("getAccessRightsForEntity",
        entityId=obj['id']
    )
    for access in access_list:
        print(json.dumps(access))

    print("")


if __name__ == "__main__":
    main()
