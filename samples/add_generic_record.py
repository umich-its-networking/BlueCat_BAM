#!/usr/bin/env python3

"""add_generic_record.py hostname type value"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging

import bluecat_bam


def main():
    """add generic record"""
    config = bluecat_bam.BAM.argparsecommon(
        "BlueCat Address Manager add generic record"
    )
    config.add_argument("hostname")
    config.add_argument("type")
    config.add_argument("data")
    config.add_argument("--ttl", default=-1)

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (_, view_id) = conn.get_config_and_view(args.configuration, args.view)
        obj_id = conn.do(
            "addGenericRecord",
            method="post",
            absoluteName=args.hostname,
            ttl=args.ttl,
            type=args.type,
            rdata=args.data,
            properties={},
            viewId=view_id,
        )

        obj = conn.do("getEntityById", method="get", id=obj_id)

        print(json.dumps(obj))


if __name__ == "__main__":
    main()
