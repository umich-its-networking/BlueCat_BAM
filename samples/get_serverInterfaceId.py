#!/usr/bin/env python

"""get_serverInterfaceId.py BDDSservername"""

# to be python2/3 compatible:
from __future__ import print_function

import logging

import bluecat_bam


__progname__ = "get_serverInterfaceId"
__version__ = "0.2"


def main():
    """get server interface id"""
    config = bluecat_bam.BAM.argparsecommon(
        "BlueCat Address Manager get_serverInterfaceId"
    )
    config.add_argument("bdds", help="BDDS server name")
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    server_name = args.bdds

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)

        interface = conn.getinterface(server_name, configuration_id)
        if interface:
            interface_id = interface["id"]
            print(interface_id)
        else:
            print("ERROR - did not find interface for", server_name)


if __name__ == "__main__":
    main()
