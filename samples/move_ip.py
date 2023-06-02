#!/usr/bin/env python3

"""move_ip.py --type type --host domain_name --new new_domain_name"""

# to be python2/3 compatible:
from __future__ import print_function

import logging
import bluecat_bam


def main():
    """move_ip.py"""
    config = bluecat_bam.BAM.argparsecommon("move_ip")
    config.add_argument("old_ip", help="DNS domain name or hostname")
    config.add_argument(
        "new_ip"
    )

    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.loglevel)

    configuration_name = args.configuration
    view_name = args.view

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:

        (configuration_id, view_id) = conn.get_config_and_view(configuration_name, view_name)

        ip_obj = conn.do(
         "getIP4Address", method="get", containerId=configuration_id, address=args.old_ip
        )
        print("old: ",ip_obj)

        chk_obj = conn.do("getIP4Address", method="get", containerId=configuration_id, address=args.new_ip )
        if chk_obj and chk_obj['id']:
            print("error, new ip exists:", chk_obj)
        else:
            result = conn.do( "moveIPObject", method="put", address=args.new_ip, objectId=ip_obj['id'], options="noServerUpdate=true" )
            #print(result)
            chk_obj = conn.do("getIP4Address", method="get", containerId=configuration_id, address=args.new_ip )
            print("new: ",chk_obj)
if __name__ == "__main__":
    main()
