#!/usr/bin/env python

"""
sort_by_special.py TYPE [--regex=REGEX] < input
where TYPE can be any of "text","number","ip","mac","version"
Allowing sorts by IP Address, MAC Address, Version number, etc
"""


# to be python2/3 compatible:
from __future__ import print_function

import sys
import logging
import re
import argparse


__progname__ = "sort_by_special"
__version__ = "0.1"


def main():
    """sort_by_special - main"""
    config = argparse.ArgumentParser(description="sort_by_special")
    types = ["text", "number", "ip", "mac", "version"]
    config.add_argument(
        "type",
        default="text",
        help="type - one of: "
        + str(types)
        + " Allowing sorts by IP Address, MAC Address, Version number, etc."
        + " (default is to sort as text)",
    )
    config.add_argument(
        "--regex",
        default="",
        help="regular expression matching the part of the line to sort by."
        + "  Default is the whole line."
        + "  Lines that do not match are output to stderr."
        + "  Then lines that match are sorted and output to stdout.",
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

    regex = args.regex
    sort_type = args.type
    logger.info("regex '%s', type '%s'", regex, sort_type)

    # iterator from stdin
    # lines = iter(sys.stdin.readline, '\n')
    lines = sys.stdin

    out = sort_by_special(lines, regex, sort_type)
    for line in out:
        print(line)


def sort_by_special(lines, regex, sort_type):  # pylint: disable=R0912
    """sort_by_special"""
    decorated = []  # decorated list to sort
    # get a line
    for line in lines:
        # remove linefeed
        line = line.rstrip("\r\n")
        # apply regex, if any
        if regex:
            m = re.search(regex, line)
            if m:
                match = m.group(1)
            else:
                print(line, file=sys.stderr)
                continue
        else:
            match = line

        # find type
        if sort_type == "text":
            sort_key = match
        elif sort_type == "number":
            s = re.search(r"(\d+(\.\d*|))(?\D)", line)
            if s:
                sort_key = float(s.group(1))
            else:
                print(line, file=sys.stderr)
                continue
        elif sort_type == "ip":
            s = re.search(r"((?:\d{1,3}\.){3}\d{1,3})($|[^\d])", line)
            if s:
                sort_key = dotdec2hex(s.group(1))
            else:
                print(line, file=sys.stderr)
                continue
        elif sort_type == "mac":
            # mac address formats:
            # 01:23:45:67:89:ab
            # 1:23:4:67:89:ab
            # 11-22-33-44-55-66
            # 0123456789ab
            # ^((?:[0-9a-fA-F]{1,2}[:-]){5}[0-9a-fA-F]{1,2}|[0-9a-fA-F]{12}|(?:[0-9a-fA-F]{4}[.]){2}[0-9a-fA-F]{4})
            s = re.search(
                r"""(^|[^:0-9a-fA-F])((?:[0-9a-fA-F]{1,2}[-:.]){5}
                [0-9a-fA-F]{1,2}|[0-9a-fA-F]{12}|(?:[0-9a-fA-F]{4}
                [.]){2}[0-9a-fA-F]{4})($|[^:0-9a-fA-F-])""",
                line,
                re.X,
            )
            if s:
                sort_key = canonical_mac(s.group(2))
                # print("mac key /%s/" % sort_key)
            else:
                print(line, file=sys.stderr)
                continue
        elif sort_type == "version":
            s = re.search(r"((?:\d+\.)+\d+)", line)
            if s:
                sort_key = [int(x) for x in s.group(1).split(".")]
            else:
                print(line, file=sys.stderr)
                continue
        else:
            print("type not implemented yet:", sort_type)
            break

        # build list of tuples to sort
        # https://wiki.python.org/moin/HowTo/Sorting/
        # #The_Old_Way_Using_Decorate-Sort-Undecorate
        decorated.append((sort_key, line))

    # sort
    decorated.sort()
    # undecorate
    out = [line for sort_key, line in decorated]
    return out


def canonical_mac(mac):
    """reformat mac address to be sure there are always two hex digits"""
    # hex_list = mac.split(":")
    hex_list = re.split(r"[-:.]", mac)
    if len(hex_list) == 1:
        hex_list = re.search(r"^(..)(..)(..)(..)(..)(..)$", mac).groups()
    # s = re.search(r"([0-9a-fA-F]{1,2}[-:.]?){5}([0-9a-fA-F]{1,2})", mac)
    # if s:
    #    for g in s.groups():
    #        print("group",g)
    out_list = []
    for h in hex_list:
        if len(h) == 1:
            h = "0" + h
        # h = format(h, "02x")
        out_list.append(h.lower())
    hexout = ":".join(out_list)
    return hexout


def dotdec2hex(dotdec):
    """convert dotted decimal to hex"""
    hexlist = []
    for decimal in dotdec.split("."):
        d = int(decimal)
        if d < 0 or d > 255:
            print(dotdec, "is not a valid dotted decimal")
            return None
        h = format(d, "02x")
        hexlist.append(h)
    hexout = ":".join(hexlist)
    return hexout


if __name__ == "__main__":
    main()
