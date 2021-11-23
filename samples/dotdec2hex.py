#!/usr/bin/env python

"""dotdec2hex.py [dotted-decimal ...]
convert dotted decimal to hex with colons
(use for MAC Addresses)"""
# translated from Perl /home/jmd/bin/dotdec2hex

import sys
import re
import argparse


def main():
    """CLI for dotdec2hex"""
    config = argparse.ArgumentParser(
        description="BlueCat Address Manager add_DNS_Deployment_Role_list"
    )
    config.add_argument(
        "dotdec",
        nargs="*",
        help="dotted decimal",
    )

    args = config.parse_args()

    if args.dotdec:
        for x in args.dotdec:
            print(dotdec2hex(x))
    else:
        with sys.stdin as f:
            for line in f:
                line = re.sub(r"(?:\r\n|\n)$", "", line, count=1)
                print(dotdec2hex(line))


def dotdec2hex(dotdec):
    """convert dotted decimal to hex"""
    hexlist = []
    for decimal in dotdec.split("."):
        d = int(decimal)
        if d < 0 or d > 255:
            print(dotdec, "is not a valid dotted decimal")
            return None
        h = format(d, "x")
        hexlist.append(h)
    hexout = ":".join(hexlist)
    return hexout


if __name__ == "__main__":
    main()
