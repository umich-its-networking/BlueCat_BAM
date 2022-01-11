#!/usr/bin/env python

"""delete_ip_address.py ip-address
requires deleting linked hostnames
DHCP free will be deleted silently
future:
DHCP Reserved will be deleted with --force
DHCP active will be deleted with --force
"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging
import datetime

import bluecat_bam


def main():
    """delete_ip_address"""
    config = bluecat_bam.BAM.argparsecommon()
    config.add_argument(
        "object_ident",
        help="Can be: entityId (all digits), individual IP Address (n.n.n.n), "
        + "IP4Network or IP4Block (n.n.n.n/...), or DHCP4Range (n.n.n.n-...).  "
        + "or a filename or stdin('-') with any of those on each line "
        + "unless 'type' is set to override the pattern matching",
    )
    # config.add_argument("ip", help="IP Address")
    config.add_argument(
        "--states",
        help="list of IP states to delete, like --states"
        + " DHCP_FREE,DHCP_ALLOCATED,DHCP_RESERVED,STATIC"
        + " (default=all)",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    ip = args.object_ident
    states = args.states

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)

        # future accept list?
        # input_list = conn.get_obj_list(args.object_ident, configuration_id, "")

        ip_obj = conn.do(
            "getIP4Address", method="get", containerId=configuration_id, address=ip
        )
        ip_id = ip_obj["id"]

        if ip_id == 0:
            print("IP Address not found: %s" % (ip))
        else:
            address = ip_obj["properties"]["address"]
            state = ip_obj["properties"]["state"]
            if not states or state in states:
                if state == "DHCP_ALLOCATED":
                    # BAM returns seconds with one decimal,
                    # datetime needs 3, so add a couple zeros
                    expiretime = datetime.datetime.fromisoformat(
                        ip_obj["properties"]["expiryTime"] + "00"
                    )
                    if expiretime > datetime.datetime.now():
                        print("warning - dhcp lease time still active", ip_obj)
                result = conn.delete_ip_obj(ip_obj)
                if result:
                    print("delete resulted in", result)
                # check if IP address still exists, should get id=0 if not
                check_ip = conn.do("getEntityById", method="get", id=ip_id)
                check_ip_id = check_ip["id"]
                if check_ip_id == 0:
                    print("Deleted IP %s %s" % (address, state))
                else:
                    print("ERROR - IP address failed to delete:", json.dumps(check_ip))
            else:
                print("skipped due to state, IP %s, state %s" % (address, state))


if __name__ == "__main__":
    main()
