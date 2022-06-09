#!/usr/bin/env python

"""add_update_hostname_ip.py hostname new_ip"""

# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging
import time

import requests

import bluecat_bam


def main():
    """add_update_hostname_ip.py - update IP of hostname"""
    config = bluecat_bam.BAM.argparsecommon("update IP of hostname")
    config.add_argument("hostname", help="fully qualified hostname")
    config.add_argument("new_ip", help="new IP Address")
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    configuration_name = args.configuration
    view_name = args.view
    hostname = args.hostname
    new_ip = args.new_ip
    record_type = "HostRecord"

    if not (configuration_name and view_name and hostname and new_ip):
        config.print_help()
        sys.exit(1)

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (_, view_id) = conn.get_config_and_view(configuration_name, view_name)

        zone_obj, shortname = conn.get_zone(hostname, view_id)
        entities = conn.do(
            "getEntitiesByNameUsingOptions",
            method="get",
            parentId=zone_obj["id"],
            name=shortname,
            type=record_type,
            options="ignoreCase=true",
            start=0,
            count=1000,
        )
        if not entities:
            print("not found, adding")
            add_host(conn, zone_obj, shortname, new_ip, view_id)
        else:
            move_host(conn, entities, zone_obj, shortname, new_ip)


def add_host(conn, zone_obj, shortname, new_ip, view_id):
    """add_host"""
    host_id = conn.do(
        "addHostRecord",
        absoluteName=shortname + "." + zone_obj["properties"]["absoluteName"],
        addresses=new_ip,
        properties="",
        ttl=-1,
        viewId=view_id,
    )
    if host_id == 0:
        print("failed to create host record", zone_obj, shortname, new_ip)


def move_host(conn, entities, zone_obj, shortname, new_ip):
    """move host to new ip"""
    # note that hostname can have more than one HostRecord
    for entity in entities:
        pass
        # **** need work here ****


def do_entities(conn, entities, zone_obj, shortname, new_zone, new_shortname):
    """update each entity"""
    for entity in entities:
        # space is to line this up with the ending print
        print("found entity ", entity)
        try:
            # match up old and new to see if short hostname, or zone, or both changed
            if new_zone["id"] == zone_obj["id"]:
                # zone changes
                if new_shortname == shortname:
                    print("ERROR - old and new name are the same?")
                else:
                    # short name changes
                    new_entity = entity
                    new_entity["name"] = new_shortname
                    resp = conn.do("update", body=entity)
                    if resp:
                        print("response to update", resp)
            else:
                if new_shortname == shortname:
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
                    new_entity["name"] = prefix + new_shortname
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
                    new_entity["name"] = new_shortname
                    resp = conn.do("update", body=entity)
                    if resp:
                        print("response to update", resp)
        except requests.exceptions.HTTPError as e:
            print("ERROR from BAM", e)
        check_entity = conn.do("getEntityById", id=entity["id"])
        print("entity is now", check_entity)


if __name__ == "__main__":
    main()
