#!/usr/bin/env python3

"""update_alias_cname.py --type type --host domain_name --new new_domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging
import os
import time

import requests

import bluecat_bam


def main():
    """update_alias_cname.py"""
    config = bluecat_bam.BAM.argparsecommon("update_alias_cname")
    config.add_argument("domain_name", help="DNS domain name or hostname")
    config.add_argument(
        "new_domain_name", help="new fqdn, same domain, just hostname change"
    )
    config.add_argument("--external",action="store_true",
        help="Point alias at External Host Record (otherwise point at normal Host Record)")

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    configuration_name = args.configuration
    view_name = args.view
    domain_name = args.domain_name
    new_domain_name = args.new_domain_name
    if args.external:
        external_text="true"
    else:
        external_text="false"


    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (_, view_id) = conn.get_config_and_view(configuration_name, view_name)

        zone, remainder = conn.get_zone(domain_name, view_id)
        entities = conn.do(
            "getEntitiesByNameUsingOptions",
            method="get",
            parentId=zone["id"],
            name=remainder,
            type="AliasRecord",
            options="ignoreCase=true",
            start=0,
            count=1000,
        )
        if not entities:
            print("not found", domain_name, "in", view_name)
            return

        if args.external:
            # getEntityByName name=bam-seb-1.umnet.umich.edu parentId=1048598 type=ExternalHostRecord
            dest_obj=conn.do("getEntityByName",name=new_domain_name, parentId=view_id, type="ExternalHostRecord"
            )
            print("ext host found:",dest_obj)
        else:
            new_zone, new_remainder = conn.get_zone(new_domain_name, view_id)
            # check for same record tyoe, or Alias (CNAME) records
            # at new_domain_name that will conflict
            type_set = {"HostRecord","AliasRecord"}
            for mytype in type_set:
                dest_entities = conn.do(
                    "getEntitiesByNameUsingOptions",
                    method="get",
                    parentId=new_zone["id"],
                    name=new_remainder,
                    type=mytype,
                    options="ignoreCase=true",
                    start=0,
                    count=1000,
                )
                print("found records:",dest_entities)
            print('new',new_zone, new_remainder)   

        print("current",entities[0])
        print("old",zone, remainder)

        update_alias(conn, entities[0], zone, remainder, new_domain_name, external_text)

def update_alias(conn, entity, zone, remainder, new_domain_name, external_text):
    '''update alias record to point to new hostname'''
    new_entity=entity.copy()
    new_entity['properties']['linkedRecordName']=new_domain_name
    print("update to", new_entity)
    result=conn.do("updateWithOptions",
        options="linkToExternalHost=" + external_text,
        body=entity
    )
    print("result",result)
    #do_entities(conn, entities, zone, remainder, new_zone, new_remainder)


def do_entities(conn, entities, zone, remainder, new_zone, new_remainder):
    """update each entity"""
    for entity in entities:
        # space is to line this up with the ending print
        print("found entity ", entity)
        try:
            # match up old and new to see if short hostname, or zone, or both changed
            if new_zone["id"] == zone["id"]:
                # zone changes
                if new_remainder == remainder:
                    print("ERROR - old and new name are the same?")
                else:
                    # short name changes
                    new_entity = entity
                    new_entity["name"] = new_remainder
                    resp = conn.do("update", body=entity)
                    if resp:
                        print("response to update", resp)
            else:
                if new_remainder == remainder:
                    # only zone changes
                    resp = conn.do(
                        "moveResourceRecord",
                        destinationZone=new_zone["properties"]["absoluteName"],
                        resourceRecordId=entity["id"],
                    )
                    if resp:
                        print("response to moveResourceRecord", resp)
                else:
                    # both zone and hostname change
                    # if both domain and name change, we need two steps, and
                    # then need to account for possible name
                    # conflicts at the mid point
                    # rename to a temp name to avoid that

                    # use both update and moveResourceRecord
                    prefix = str(int(time.time()))
                    # print("prefix", prefix)
                    # short name changes
                    new_entity = entity
                    new_entity["name"] = prefix + new_remainder
                    resp = conn.do("update", body=entity)
                    if resp:
                        print("response to update", resp)
                    # update zone
                    resp = conn.do(
                        "moveResourceRecord",
                        destinationZone=new_zone["properties"]["absoluteName"],
                        resourceRecordId=entity["id"],
                    )
                    if resp:
                        print("response to moveResourceRecord", resp)
                    # update name to final
                    new_entity["name"] = new_remainder
                    resp = conn.do("update", body=entity)
                    if resp:
                        print("response to update", resp)
        except requests.exceptions.HTTPError as e:
            print("ERROR from BAM", e)
        check_entity = conn.do("getEntityById", id=entity["id"])
        print("entity is now", check_entity)


if __name__ == "__main__":
    main()
