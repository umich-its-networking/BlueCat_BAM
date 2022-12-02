#!/usr/bin/env python3

"""add_external_host.py hostname"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging

import bluecat_bam


def main():
    """add external host"""
    config = bluecat_bam.BAM.argparsecommon("BlueCat Address Manager add external host")
    config.add_argument("hostname")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (_, view_id) = conn.get_config_and_view(args.configuration, args.view)
        obj_id = conn.do(
            "addExternalHostRecord",
            method="post",
            name=args.hostname,
            viewId=view_id,
            properties={},
        )

        obj = conn.do("getEntityById", method="get", id=obj_id)

        print(json.dumps(obj))


if __name__ == "__main__":
    main()
