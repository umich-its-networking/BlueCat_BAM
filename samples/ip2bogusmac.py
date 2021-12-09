#!/usr/bin/env python

"""
ip2bogusmac.py [ip]
IP Address is converted to a MAC Address in the self-assigned range
in the form fe-ff-XX-XX-XX-XX
Used to turn STATIC entries into DHCP_RESERVED so that they are
automatically excluded from DHCP ranges
"""


# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging
import re
import argparse


__progname__ = "ip2bogusmac"
__version__ = "0.1"


def main():
    """ip2bogusmac - main"""
    config = argparse.ArgumentParser(description="ip2bogusmac")
    config.add_argument(
        "ip",
        help="IP Address",
    )
    config.add_argument(
        "--logging",
        "-l",
        help="log level, default WARNING (30)",
        default="WARNING",
    )
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    ip = args.ip

    out = ip2bogusmac(ip)
    print(out)


def ip2bogusmac(ip):
    """ip2bogusmac - return mac that encodes the IP as hex
    in the form fe:ff:XX:XX:XX:XX"""
    logger = logging.getLogger()
    logger.info(ip)
    m=re.search(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})",ip)
    logger.info(m.lastindex)
    if m.lastindex == 4:
        hexlist = ["fe","ff"]
        for g in m.groups():
            d = int(g)
            if d < 0 or d > 255:
                print(dotdec, "is not a valid dotted decimal")
                return None
            h = format(d, "02x")
            hexlist.append(h)
            logger.info("dec %s, hex %s",d,h)
        hexout = ":".join(hexlist)
    else:
        hexout=None
    return hexout


if __name__ == "__main__":
    main()
