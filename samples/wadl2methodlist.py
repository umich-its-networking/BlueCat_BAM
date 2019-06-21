#!/usr/bin/env python

"""read wadl, output list of http methods and api commands"""

# to be python2/3 compatible:
from __future__ import print_function
from __future__ import unicode_literals

import xmltodict

with open("/dev/stdin") as f:
    wadl = xmltodict.parse(f.read())
    methodlist = wadl["application"]["resources"]["resource"]["resource"]
    for c in methodlist:
        print("%s %s" % (c["method"]["@name"], c["method"]["@id"]))
