#!/usr/bin/env python

"""delete_obj.py [-q] obj_id
If not -q, then get and print object first
Then delete the object
"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging
import re
import requests

import bluecat_bam


__progname__ = "delete_obj.py"
__version__ = "0.1"


def main():
    """delete_obj"""

    config = bluecat_bam.BAM.argparsecommon("delete object")
    config.add_argument("obj_id", help="object id, or file name")
    config.add_argument(
        "--quiet", "-q", help="quiet - do not get and print object", action="store_true"
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    quiet = args.quiet
    obj_id = args.obj_id

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        id_match = re.match(r"\d+$", obj_id)
        if id_match:
            del_id(obj_id, conn, quiet)
        else:
            # for line in fileinput.input(encoding="utf-8"):
            with open(obj_id, "r") as fd:
                for line in fd:
                    del_id(line.rstrip(), conn, quiet)


def del_id(obj_id, conn, quiet):
    """delete object by id"""
    logger = logging.getLogger()
    logger.info("deleting: %s", obj_id)
    result = None
    if not quiet:
        obj = conn.do("getEntityById", id=obj_id)
        if obj["id"] == 0:
            print("id not found:", obj_id)
            return
        print(json.dumps(obj))
    try:
        result = conn.do("delete", objectId=obj_id)
    except requests.exceptions.HTTPError as e:
        print("error:", e)
    if result:
        print("result:", result)


if __name__ == "__main__":
    main()
