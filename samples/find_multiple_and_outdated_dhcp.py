#!/usr/bin/env python

"""
find_multiple_and_outdated_dhcp.py < list-of-networkIP
[--cfg configuration] [--view viewname]
"""


# to be python2/3 compatible:
from __future__ import print_function

import logging

import bluecat_bam


__progname__ = "find_multiple_and_outdated_dhcp"
__version__ = "0.1"


def main():
    """find_multiple_and_outdated_dhcp.py"""
    config = bluecat_bam.BAM.argparsecommon(
        "Find multiple DHCP entries"
        + " for the same MAC Address in the same Network, or out of date entries"
        + "and optionally delete them"
    )
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    # add --delete option ****
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    configuration_name = args.configuration
    object_ident = args.object_ident
    rangetype = ""

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(configuration_name)

        obj_list = conn.get_obj_list(object_ident, configuration_id, rangetype)
        logger.info("obj_list: %s", obj_list)

        for entity in obj_list:
            entityId = entity["id"]
            matching_list = conn.get_ip_list(entityId)  # , states=["DHCP_ALLOCATED"])
            mac_dict = {}
            for ip in matching_list:
                obj_mac = ip["properties"].get("macAddress")
                if obj_mac:
                    dup_ip = mac_dict.get(obj_mac)
                    if dup_ip:
                        print(
                            dup_ip["properties"]["address"],
                            dup_ip["properties"]["state"],
                            "and",
                            ip["properties"]["address"],
                            ip["properties"]["state"],
                            "both have mac",
                            obj_mac,
                        )
                        # delete the dup or the older entry
                        # need to check state
                    else:
                        mac_dict[obj_mac] = ip


if __name__ == "__main__":
    main()
