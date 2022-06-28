#!/usr/bin/env python

"""get_fqdn.py domain_name [--type HostRecord]"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging

import bluecat_bam


__progname__ = "get_fqdn"
__version__ = "0.1"


def main():
    """get_fqdn"""
    config = bluecat_bam.BAM.argparsecommon("Get fully qualified domain name object")
    config.add_argument(
        "--type",
        help="DNS record type, like HostRecord, AliasRecord, TXTRecord, "
        + "GenericRecord, etc, or Entity to get all types",
        default="Entity",
    )
    config.add_argument("domain_name", help="DNS domain name or hostname")
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    record_type = args.type

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (_, view_id) = conn.get_config_and_view(args.configuration, args.view)

        obj_list = conn.get_obj_list(args.domain_name, view_id, record_type)

        for domain_name in obj_list:
            get_fqdn(domain_name, view_id, record_type, conn)


def get_fqdn(domain_name, view_id, record_type, conn):
    """get object given fqdn and record type"""
    entities = conn.get_fqdn(domain_name, view_id, record_type)
    for entity in entities:
        print(json.dumps(entity))


if __name__ == "__main__":
    main()
