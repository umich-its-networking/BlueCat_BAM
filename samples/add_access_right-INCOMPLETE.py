#!/usr/bin/env python

"""
add_access_right.py object group value overrides properties

For the specified object, add the specified access rights for the group(or user)
"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging

import bluecat_bam


__progname__ = "add_access_right.py"
__version__ = "0.1"


def main():
    """get_deployment_options"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    config.add_argument(
        "group",
        help='group or user to grant access'
    )
    config.add_argument(
        "value",
        nargs='?',
        default="FULL",
        help='optional - Access right - FULL, VIEW, etc, default is FULL'
    )
    config.add_argument(
        "overrides",
        default='',
        help='optional - like "DNSOption=VIEW|DNSRawOption=VIEW"'
    )
    config.add_argument(
        "properties",
        default='',
        help='optional - other settings like "deploymentAllowed=false|workflowLevel=NONE|"'
    )

    args = config.parse_args()
    object_ident = args.object_ident
    rangetype = args.type

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)
        
        # get group ********
        group_id = get_group_or_user_id(conn, args.group)

        rangetype=None
        obj_list = conn.get_obj_list(object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for obj in obj_list:
            add_access(conn, obj, group_id, args.value, args.overrides, args.properties)

def get_group_or_user_id(conn, group_name):
    group_obj = conn.do(
        "getEntityByName", method="get", parentId=0, name=group_name, type="UserGroup"
    )
    group_id = group_obj["id"]
    print(f'group {group_id}')
    return group_id

def add_access(conn, obj, group_id, value, overrides, properties):
    '''add access to object for group'''
    # get existing access rights to look for conflicts
    existing = conn.do(
        "getAccessRightsForUser", userId=group_id, start=0, count=99999
    )
    existing_by_id = {right["entityId"]: right for right in existing}

    # add access rights to to_group
    for accessright in accessrights:
        if existing_by_id.get(accessright["entityId"]):
            print("access right conflict")
            print("existing: %s" % (existing_by_id[accessright["entityId"]]))
            print("new: %s" % (accessright))
        else:
            print("add access right: %s" % (accessright))
            accessrightid = conn.do(
                "addAccessRight",
                entityId=accessright["entityId"],
                userId=group_id,
                value=accessright["value"],
                overrides=accessright["overrides"],
                properties=accessright["properties"],
            )

def get_deployment_option(conn, args, obj):
    """get deployment options for the range"""
    logger = logging.getLogger()
    optionlist = args.options
    print(obj)
    obj_id = obj["id"]

    options = conn.do(
        "getDeploymentOptions", entityId=obj_id, optionTypes="", serverId=-1
    )
    logger.info(json.dumps(options))
    for option in options:
        if optionlist and option.get("name") not in optionlist:
            continue

        print(json.dumps(option))
    print()  # blank line after each set of lines


if __name__ == "__main__":
    main()
