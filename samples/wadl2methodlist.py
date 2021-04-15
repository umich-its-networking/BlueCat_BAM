#!/usr/bin/env python

"""read wadl, output list of http methods and api commands"""

# to be python2/3 compatible:
from __future__ import print_function
from __future__ import unicode_literals

import json
import xmltodict

with open("/dev/stdin") as f:
    wadl = xmltodict.parse(f.read())
    methodlist = wadl["application"]["resources"]["resource"]["resource"]
    for c in methodlist:
        for c_name, c_value in c.items():
            if c_name == "@path":
                pass  # same info as @id below
            elif c_name == "method":
                f_out = ""
                for d_name, d_value in c_value.items():
                    if d_name == "@id":
                        api_method = d_value  # api method
                    elif d_name == "@name":
                        name = d_value  # http method
                    elif d_name == "request":
                        # print("d_value: %s" % (json.dumps(d_value)))
                        for e_name, e_value in d_value.items():
                            # print("e_name: %s" % (e_name))
                            if e_name == "param":
                                # print("e_name,e_value: %s, %s" % (json.dumps(e_name),
                                #     json.dumps(e_value)))
                                if isinstance(e_value, list):
                                    for f in e_value:
                                        # print("f: %s" % (json.dumps(f)))
                                        f_out += (
                                            " "
                                            + f["@name"]
                                            + "="
                                            + f["@type"].split(":")[1]
                                        )
                                else:
                                    f = e_value
                                    # print("f: %s" % (json.dumps(f)))
                                    f_out = (
                                        " "
                                        + f["@name"]
                                        + "="
                                        + f["@type"].split(":")[1]
                                    )
                                # print("partial f_out: %s" % (f_out))
                            elif e_name == "representation":
                                f = e_value
                                f_out += " data=" + f["@mediaType"]
                            else:
                                print(
                                    "not recognized e: %s %s"
                                    % (e_name, json.dumps(e_value))
                                )
                    elif d_name == "response":
                        pass  # not useful enough to show
                        # print("d_value: %s" % (json.dumps(d_value)))
                        # f = d_value
                        # f_out += " " + d_name + "=" +
                        #          f["representation"]['@mediaType']
                    else:
                        print("not recognized d: %s %s" % (d_name, json.dumps(d_value)))
                print("%s %s%s" % (name, api_method, f_out))
            else:
                print(
                    "no method for: %s, %s" % (json.dumps(c_name), json.dumps(c_value))
                )
        # print("old: %s" % (out))
