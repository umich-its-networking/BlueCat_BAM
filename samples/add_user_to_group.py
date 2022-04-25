#!/usr/bin/env python

"""add_user_to_group.py user_name 'group_name' '"""

# to be python2/3 compatible:
from __future__ import print_function

import os
import json
import argparse
import logging

import bluecat_bam

def main():
    """add user to group"""
    config = bluecat_bam.BAM.argparsecommon(
        "BlueCat Address Manager add user to group"
    )
    config.add_argument("user_name")
    config.add_argument("group_name")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(configuration_name)

        group_obj = conn.do(
            "getEntityByName",
            parentId=0,
            name=args.group_name,
            type="UserGroup"
        )
        if (not group_obj) or group_obj['id'] == 0:
            print("group not found: %s" % (args.group_name))
            return
        group_id=group_obj['id']

        user_obj = conn.do(
            "getEntityByName",
            parentId=0,
            name=args.user_name,
            type="User"
        )
        if (not user_obj) or user_obj['id'] == 0:
            print("user not found: %s" % (args.user_name))
            return
        user_id=user_obj['id']

        user_groups = conn.do(
            "getLinkedEntities",
            entityId=user_id,
            type="UserGroup",
            start=0,
            count=1000
        )
        for group in user_groups:
            if group['id'] == group_id:
                print("user: %s already in group: %s" % (args.user_name, args.group_name))
                return

        response = conn.do(
            "linkEntities",
            entity1Id=user_id,
            entity2Id=group_id,
            properties=''
        )
        if response:
            print(response)
        print("added user: %s to group: %s" % (args.user_name, args.group_name))


if __name__ == "__main__":
    main()
