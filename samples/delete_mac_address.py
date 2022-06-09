#!/usr/bin/env python

"""delete_mac_address.py mac-address
requires deleting or unlinking IP addresses
DHCP free will be deleted silently
future:
DHCP Reserved will be deleted with --force
DHCP active will be deleted with --force
"""

# to be python2/3 compatible:
from __future__ import print_function

import json
import logging

import bluecat_bam


__progname__ = "delete_mac_address.py"
__version__ = "0.1"


def main():
    """delete_mac_address"""

    config = bluecat_bam.BAM.argparsecommon(
        "delete mac address, including linked DHCP reserved IP's"
    )
    config.add_argument("mac", help="MAC Address or id, or file name")
    config.add_argument(
        "--force",
        "-f",
        help="delete active and DHCP Reserved also",
        action="store_true",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    mac = args.mac
    force = args.force
    rangetype = "MACAddress"

    with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
        (configuration_id, _) = conn.get_config_and_view(args.configuration)

        entity_list = conn.get_obj_list(mac, configuration_id, rangetype)
        for mac_obj in entity_list:
            mac_id = mac_obj.get("id")

            if mac_obj["type"] != "MACAddress":
                print("error, not a MACAddress:", mac)
                continue

            mac = mac_obj["properties"]["address"]

            ip_obj_list = conn.do(
                "getLinkedEntities",
                entityId=mac_id,
                type="IP4Address",
                start=0,
                count=9999,
            )

            print("obj:", json.dumps(mac_obj))
            print("linked IPv4:", json.dumps(ip_obj_list))
            out = mac
            for ip_obj in ip_obj_list:
                out = (
                    out
                    + " "
                    + ip_obj["properties"]["address"]
                )
                expiry = ip_obj["properties"].get("expiryTime") # no expiry for DHCP_RESERVED
                if expiry:
                    out = out + " " + expiry
                state = ip_obj["properties"]["state"]
                if state == "DHCP_FREE" or (
                    force and state in ("DHCP_ALLOCATED", "DHCP_RESERVED")
                ):
                    if state == "DHCP_ALLOCATED":
                        # change to dhcp reserved with a fake mac address, then delete
                        result = conn.do(
                            "changeStateIP4Address",
                            addressId=ip_obj["id"],
                            targetState="MAKE_DHCP_RESERVED",
                            macAddress="deadbeef1234",
                        )
                        print("change to reserved first, result: ", result)
                    result = conn.do(
                        "deleteWithOptions",
                        method="delete",
                        objectId=ip_obj["id"],
                        options="noServerUpdate=true|deleteOrphanedIPAddresses=true|",
                    )
                    # check if IP address still exists, should get id=0 if not
                    check_ip = conn.do("getEntityById", method="get", id=ip_obj["id"])
                    check_ip_id = check_ip["id"]
                    if check_ip_id == 0:
                        print("Deleted IP %s" % (ip_obj["properties"]["address"]))
                    else:
                        print("ERROR - IP address failed to delete:")
                        print(json.dumps(check_ip))
                else:
                    print(
                        "not DHCP_FREE, IP %s, state %s"
                        % (
                            ip_obj["properties"]["address"],
                            ip_obj["properties"]["state"],
                        )
                    )
            result = conn.do("delete", method="delete", objectId=mac_obj["id"])
            # check if MAC address still exists, should get id=0 if not
            check_mac = conn.do("getEntityById", method="get", id=mac_obj["id"])
            check_mac_id = check_mac["id"]
            if check_mac_id == 0:
                print("Deleted MAC ", end="")
            else:
                print("ERROR - MAC address failed to delete:")
                print(json.dumps(check_mac))
            print(out)


if __name__ == "__main__":
    main()
