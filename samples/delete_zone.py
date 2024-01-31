#!/usr/bin/env python

"""delete_zone.py zone-name
automatically deletes linked records
limited to 10 child records, or it will refuse to delete the zone
will also refuse if there are any subzones
"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging
import datetime

import bluecat_bam


def main():
    """delete_zone"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "zone",
        help="Can be: entityId (all digits), zone name (fqdn), "
        + "or a filename or stdin('-') with any of those on each line "
    )
    config.add_argument(
        "--noverify",
        help="do not verify that the IP was deleted" + "this doubles the speed",
        action="store_true",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    noverify = args.noverify

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, view_id) = conn.get_config_and_view(args.configuration,args.view)

        # future accept list?  object_ident, containerId, object_type, view_id=None
        input_list = conn.get_obj_list(args.zone, view_id, "Zone", view_id)
        if len(input_list) == 0:
            print("WARNING - nothing found for: %s" % (args.zone))
        for obj in input_list:
            if obj["type"] == "Zone":
                delete_zone_if_ok(obj,conn, noverify)
            else:
                print("ERROR - not a zone: %s %s" % (obj['name'],obj["type"]))

def delete_zone_if_ok(obj,conn, noverify):
    '''delete zone if checks are ok'''
    child_list=get_child_list(obj, conn)
    if len(child_list) > 10:
        print("ERROR - refuse to delete zone with more than 10 child records: %s" % ( obj["properties"]["absoluteName"]))
        return
    for child in child_list:
        if child['type'] == "Zone":
            print("ERROR - refuse to delete zone with sub-zones: %s"%(obj["properties"]["absoluteName"]))
            return
    del_obj(obj, conn, noverify)

def get_child_list(obj, conn):
    """get children of object"""
    child_list = conn.get_bam_api_list(
        "getEntities",
        parentId=obj["id"],
        type="Entity",
    )
    return child_list


def del_obj(obj, conn, noverify):
    """delete obj and verify"""
    obj_id=obj['id']
    result = conn.do("delete", objectId=obj_id)
    if result:
        print("delete resulted in", result)
    if noverify:
        print("Deleted zone %s" % (obj["properties"]["absoluteName"]))
    else:
        # check if object still exists, should get id=0 if not
        check_obj = conn.do("getEntityById", method="get", id=obj_id)
        check_obj_id = check_obj["id"]
        if check_obj_id == 0:
            print("Deleted zone %s" % (obj["properties"]["absoluteName"]))
        else:
            print("ERROR - zone failed to delete:", json.dumps(check_obj))


if __name__ == "__main__":
    main()
