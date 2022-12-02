#!/usr/bin/env python

"""update_hostname.py --type type --host domain_name --new new_domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging
import time

import requests

import bluecat_bam


def main():
    """update_hostname.py - update hostname and/or domain"""
    config = bluecat_bam.BAM.argparsecommon("Get fully qualified domain name object")
    config.add_argument(
        "--type", help="DNS record type, default HostRecord", default="HostRecord"
    )
    config.add_argument("domain_name", help="DNS domain name or hostname")
    config.add_argument(
        "new_domain_name", help="new fqdn, same domain, just hostname change"
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    configuration_name = args.configuration
    view_name = args.view
    record_type = args.type
    domain_name = args.domain_name
    new_domain_name = args.new_domain_name

    if not (
        configuration_name
        and view_name
        and record_type
        and domain_name
        and new_domain_name
    ):
        config.print_help()
        sys.exit(1)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (_, view_id) = conn.get_config_and_view(configuration_name, view_name)

        zone, remainder = conn.get_zone(domain_name, view_id)
        entities = conn.do(
            "getEntitiesByNameUsingOptions",
            method="get",
            parentId=zone["id"],
            name=remainder,
            type=record_type,
            options="ignoreCase=true",
            start=0,
            count=1000,
        )
        if not entities:
            print("not found", domain_name, record_type, view_name)
            return

        new_zone, new_remainder = conn.get_zone(new_domain_name, view_id)
        # check for same record tyoe, or Alias (CNAME) records
        # at new_domain_name that will conflict
        type_set = {record_type, "AliasRecord"}
        for mytype in type_set:
            alias_entities = conn.do(
                "getEntitiesByNameUsingOptions",
                method="get",
                parentId=new_zone["id"],
                name=new_remainder,
                type=mytype,
                options="ignoreCase=true",
                start=0,
                count=1000,
            )
            if alias_entities:
                print(
                    "ERROR - conflicting record exists at new domain name",
                    alias_entities,
                )
                return

        do_entities(conn, entities, zone, remainder, new_zone, new_remainder)


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
