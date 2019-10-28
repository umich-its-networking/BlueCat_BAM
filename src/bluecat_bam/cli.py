#!/usr/bin/env python

"""BlueCat Address Manager (BAM) REST CLI
using the API Python module

Author Bob Harold, rharolde@umich.edu
Date 2018/05/11, 2019/05/08
Copyright (C) 2018,2019 Regents of the University of Michigan
Apache License Version 2.0, see LICENSE file
This is a community supported open source project, not endorsed by BlueCat.
"BlueCat Address Manager" is a trademark of BlueCat Networks (USA) Inc. and its
affiliates.

See README.md for installation instructions.

Use on the command line as a CLI, putting the setup in the environment:
cat > mybluecat.env <<EOF
export BLUECAT_SERVER=bluecatservername.domain.example
export BLUECAT_USERNAME=myusername
export BLUECAT_PASSWORD=mypassword
EOF
source mybluecat.env
bam getEntityByName method=get parentId=0 name=admin type=User
{"type": "User", "properties": {"firstname": "admin", "lastname": "admin",
"userType": "ADMIN", "userAccessType": "GUI", "email": "admin@domain.example"},
"name": "admin", "id": 3}

The CLI includes verbose options, and can read server,username, and password from
environment variables.  See help:
bam -h

Output can be any of:
JSON dictionary (usually an entity)
JSON list of dictionaries (like a list of entities)
JSON string (in quotes)
boolean (true or false)
long integer (id of an entity, no quotes)
null - returned as those 4 characters, without quotes
       (null does not indicate success, only that the syntax was correct)

If the dictionary has id: 0, that usually means that nothing was returned.
The output, if JSON, can be fed to "jq" to further process the data.

"HTTPError: 500 Server Error" can be caused by lack of access rights.

Written to run under both Python2 and Python3, since the BAM (v8.3.2) has only Python2.
Using 'black' to enforce format.
This passes pylint and flake8 with minor exceptions, see .pylintrc and .flake8
Also passes bandit security linter.

Column ruler: (88 wide)
         1         2         3         4         5         6         7         8
123456789.123456789.123456789.123456789.123456789.123456789.123456789.123456789.12345678
"""

# to be python2/3 compatible:
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import logging
import json
import argparse
from bluecat_bam.api import BAM

# double underscore names
__progname__ = "cli"
__version__ = "0.2.6"


def main():
    """CLI - Command Line Interface"""
    config = argparse.ArgumentParser(
        description="BlueCat Address Manager raw JSON REST API python module and CLI"
    )
    config.add_argument(
        "--server",
        "-s",
        # env_var="BLUECAT_SERVER",
        default=os.getenv("BLUECAT_SERVER"),
        help="BlueCat Address Manager hostname",
    )
    config.add_argument(
        "--username",
        "-u",
        # env_var="BLUECAT_USERNAME",
        default=os.getenv("BLUECAT_USERNAME"),
    )
    config.add_argument(
        "--password",
        "-p",
        # env_var="BLUECAT_PASSWORD",
        default=os.getenv("BLUECAT_PASSWORD"),
        help="password in environment, should not be on command line",
    )
    config.add_argument(
        "--raw",
        "-r",
        default=os.getenv("BLUECAT_RAW"),
        help="set to true to not convert strings like 'name=value|...' "
        + "to dictionaries on output.  Will accept either format on input.",
    )
    config.add_argument(
        "--raw_in",
        default=os.getenv("BLUECAT_RAW_IN"),
        help="set to true to not convert input strings from json to 'name-value|...', useful for txt records with json content",
    )
    config.add_argument(
        "--version", action="version", version=__progname__ + ".py " + __version__
    )
    config.add_argument(
        "--logging",
        "-l",
        help="log level, default WARNING (30),"
        + "caution: level DEBUG(10) or lower will show the password in the login call",
        default=os.getenv("BLUECAT_LOGGING", "WARNING"),
    )
    config.add_argument(
        "command", help="BlueCat REST API command, for example: getEntityById"
    )
    config.add_argument("args", nargs=argparse.REMAINDER)
    args = config.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    # should use a 'comprehension' ?? ***
    params = {}  # create the params dictionary
    params["body"] = None  # default value
    for pair in args.args:
        try:
            name, value = pair.split("=", 1)  # "1" means only split on first "="
            params[name] = value
        except ValueError:
            print("ERROR in argument '%s'" % (pair))
            print("Type '%s -h' for help" % (os.path.basename(sys.argv[0])))
            # config.print_help()  # printing full help on every mistake is too much
            # raise ValueError  # stacktrace here is not useful
            sys.exit(1)

    if not (args.server and args.username and args.password):
        print(
            "server, username, and password are required.\n",
            "Please put them in the environment.\n",
        )
        print("Type '%s -h' for help" % (os.path.basename(sys.argv[0])))
        # config.print_help()  # printing full help on every mistake is too much
        # raise ValueError  # stacktrace here is not useful
        sys.exit(2)
    logging.debug("raw: %s", args.raw)
    if not args.raw:
        args.raw = False
        logging.debug("raw_in changed to False")
    else:
        args.raw = make_bool(args.raw)
        logging.debug("raw_in made bool")
    '''
    isinstance(args.raw, bool):
        pass
    elif args.raw.lower() == "false":
        args.raw = False
    elif args.raw.lower() == "true":
        args.raw = True
    else:
        print("ERROR: --raw must be True or False, not: ", args.raw, file=sys.stderr)
    '''
    logging.debug("raw_in: %s", args.raw_in)
    if not args.raw_in:
        args.raw_in = False
    else:
        args.raw_in = make_bool(args.raw_in)
    logging.debug("raw_in: %s", args.raw_in)

    # call MAIN
    with BAM(args.server, args.username, args.password, raw=args.raw, raw_in=args.raw_in) as conn:
        entity = conn.do(args.command, **params)
        print(json.dumps(entity))


def make_bool(var):
    if isinstance(var, bool):
        pass
        logging.debug("var already bool %s", var)
    elif var.lower() == "false":
        var = False
        logging.debug("var false")
    elif var.lower() == "true":
        var = True
        logging.debug("var true")
    else:
        print("ERROR: %s must be True or False, not: %s" % (var.__name__,var))
    return var


if __name__ == "__main__":
    main()
