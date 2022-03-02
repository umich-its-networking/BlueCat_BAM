#!/usr/bin/env python

"""find_parent_of_type.py config view type domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging

import bluecat_bam


def main():
    """find parent object of specified type"""
    config = bluecat_bam.BAM.argparsecommon("find parent object of specified type")
    config.add_argument("id", help="id of starting object")
    config.add_argument("type", help="object type to find, searching up the tree")
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    start_id = args.id
    object_type = args.type

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        parent_obj = conn.find_parent_of_type(start_id, object_type)

        print(json.dumps(parent_obj))


if __name__ == "__main__":
    main()
