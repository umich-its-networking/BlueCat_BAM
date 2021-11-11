#!/usr/bin/env python

"""BlueCat Address Manager (BAM) REST API Python2 module

Author Bob Harold, rharolde@umich.edu
Date 2018/05/11, 2019/04/11
Copyright (C) 2018,2019 Regents of the University of Michigan
Apache License Version 2.0, see LICENSE file
This is a community supported open source project, not endorsed by BlueCat.
"BlueCat Address Manager" is a trademark of BlueCat Networks (USA) Inc. and its
affiliates.

See README.md for installation instructions.

Use as a Python module like:
import json
import bluecat_bam
with BAM(server, username, password) as conn:
    r = conn.do('getEntityByName', method='get', parentId=0, name='admin', type='User')
    print(json.dumps(r))

Sample output:
{"type": "User", "properties": {"firstname": "admin", "lastname": "admin",
"userType": "ADMIN", "userAccessType": "GUI", "email": "admin@domain.example"},
"name": "admin", "id": 3}

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
#        1         2         3         4         5         6         7         8
123456789.123456789.123456789.123456789.123456789.123456789.123456789.123456789.12345678
"""

# to be python2/3 compatible:
from __future__ import print_function
from __future__ import unicode_literals

import sys
import logging
import json
import argparse
import os
import re
import requests


# double underscore names
__progname__ = "api"
__version__ = "0.2.7"

# python2/3 compatability
try:
    basestring
except NameError:
    basestring = str  # pylint: disable=invalid-name,redefined-builtin


class BAM(requests.Session):  # pylint: disable=R0902
    """subclass requests and
    redefine requests.request to a simpler BlueCat interface"""

    def __init__(
        self,
        server,
        username,
        password,
        raw=False,
        raw_in=False,
        timeout=None,
        max_retries=None,
    ):
        """login to BlueCat server API, get token, set header"""
        self.username = username
        self.password = password
        self.timeout = timeout
        self.raw = bool(raw)
        logging.info("raw: %s", self.raw)
        self.raw_in = bool(raw_in)
        logging.info("raw_in: %s", self.raw_in)
        if not (server and username and password):
            print("server, username, and password are required.\n")
            raise requests.RequestException
        self.mainurl = self.convert_url(server)
        logging.info("url: %s", self.mainurl)

        requests.Session.__init__(self)
        if max_retries:
            adapter = requests.adapters.HTTPAdapter(max_retries=max_retries)
            url_prefix = self.mainurl.split("://", 1)[0] + "://"
            self.mount(url_prefix, adapter)
        self.login()

    # __enter__ from our parent class returns the Session object for us

    def __exit__(self, *args):
        self.logout()

    @staticmethod
    def convert_url(server):
        """Convert server string to full url,
        'server' can optionally include the prefix and port, like:
        server.example.com
        server.example.com:8080
        http://server.example.com
        """
        if "://" in server:
            # if yes, use the url method
            mainurl = server + "/Services/REST/v1/"
        else:
            # if not, default to https://
            mainurl = "https://" + server + "/Services/REST/v1/"
        return mainurl

    def login(self):
        """login, get token"""
        try:
            response = self.get(
                self.mainurl + "login?",
                params={"username": self.username, "password": self.password},
            )
        except requests.exceptions.ConnectionError as errormsg:
            print("failed to login: ", errormsg)
            raise requests.exceptions.ConnectionError
        if response.status_code != 200:
            print(response.json(), file=sys.stderr)
            raise requests.HTTPError
        self.token = str(response.json())
        self.token = self.token.split()[2] + " " + self.token.split()[3]
        self.token_header = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }
        # s.headers.update({'x-test': 'true'})
        self.headers.update(
            {"Authorization": self.token, "Content-Type": "application/json"}
        )

    def logout(self):
        """log out of BlueCat server, return nothing"""
        self.get(self.mainurl + "logout?", headers=self.token_header)

    def do(self, command, method=None, data=None, **kwargs):
        # pylint: disable=invalid-name,R0912
        """run any BlueCat REST API command"""
        # method = kwargs.pop("method")
        # Convert properties from dict-in-string to dict if needed
        # if properties:
        #     properties = self.convert_data(properties)
        if not method:
            method = self.get_method_from_command(command)
        if not method:
            print("ERROR - method not specified and could not be derived")
            raise ValueError
        try:
            body = kwargs.pop("body")
            if body:
                data = body
        except KeyError:
            pass
        if not self.raw_in:
            data = self.convert_data(data)  # Convert data if needed
        try:
            properties = kwargs.get("properties")
            if not self.raw_in:
                properties = self.convert_dict_in_str_to_dict(properties)
                kwargs["properties"] = self.convert_dict_to_str(properties)
            logging.debug("properties converted: %s", properties)
        except KeyError:
            logging.debug("no properties")
        try:
            overrides = kwargs.get("overrides")
            if not self.raw_in:
                overrides = self.convert_dict_in_str_to_dict(overrides)
                kwargs["overrides"] = self.convert_dict_to_str(overrides)
        except KeyError:
            pass
        response = self.request(
            method,
            self.mainurl + command + "?",
            # params={"properties": properties, kwargs},
            # headers=self.token_header,
            data=data,
            params=kwargs,
            timeout=self.timeout,
        )
        logging.info(vars(response.request))
        logging.info("response: %s", response.text)
        logging.debug("headers: %s", response.headers)
        logging.debug("len: %s", response.headers.get("Content-Length"))
        # print("status_code: %s" % response.status_code)
        if response.status_code != 200:
            print(response.text, file=sys.stderr)
        response.raise_for_status()
        # check type of response
        logging.info(response)
        if response.headers.get("Content-Length") == "0":
            obj = None  # void (null) response
        else:
            obj = response.json()
        if not self.raw:
            obj = self.convert_response(obj)
        return obj
        # pylint: enable=invalid-name,R0912

    @staticmethod
    def convert_dict_in_str_to_dict(data):
        """data, properties, and overrides can be dict, but passed as json string,
        especially from cli"""
        if data and isinstance(data, basestring) and data[0] == "{":
            try:
                data = json.loads(data)
            except ValueError:
                print("Failed to convert data '%s' from string to dict" % (data))
        return data

    # @staticmethod
    def convert_data(self, data):
        """data is always None or dict or a json string containing a dict
        only need to call this if data is not None"""
        logging.debug("data type is: %s", type(data).__name__)
        logging.debug(data)
        # convert string to dict if needed
        if data:
            if isinstance(data, basestring):
                data = json.loads(data)
            newdata = {}
            # convert inside dict
            for key, value in data.items():
                # convert sub-dict to string, for properties and overrides
                if isinstance(value, dict):
                    value = self.convert_dict_to_str(value)
                newdata[key] = value
            data = newdata
        logging.debug("converted data type is: %s", type(data).__name__)
        logging.debug(data)
        return json.dumps(data)

    @staticmethod
    def convert_dict_to_str(value):
        """convert dict to string name=value|..."""
        if isinstance(value, dict):
            value = "|".join(k + "=" + str(v) for k, v in value.items()) + "|"
            # value = "|".join([k + "=" + str(v) for k, v in value.items()]) + "|"
        return value

    # @staticmethod
    def convert_response(self, obj):
        """check types of response and convert if needed"""
        if obj is None:
            logging.info("response is null")
        elif isinstance(obj, basestring):
            logging.info("response is string")
            obj = self.convert_str_to_dict(obj)
        elif isinstance(obj, dict):
            logging.info("response is dict")
            obj = self.convert_dict_entries(obj)
        elif isinstance(obj, list):
            logging.info("response is list")
            obj = [self.convert_dict_entries(item) for item in obj]
        elif isinstance(obj, bool):
            logging.info("response is bool")
        elif isinstance(obj, int):  # note that bool is subset of int, so order is key
            logging.info("response is int")
        else:
            print("ERROR - response not recognized", file=sys.stderr)
            raise ValueError
        return obj

    # @staticmethod
    def convert_dict_entries(self, obj):
        """convert each value string in dict"""
        return {k: self.convert_str_to_dict(v) for k, v in obj.items()}

    @staticmethod
    def convert_str_to_dict(value):
        """convert string to dict"""
        if isinstance(value, basestring) and "|" in value:
            value = dict(
                # using a python "generator", not a "comprehension"
                item.split("=", 1)
                for item in value.split("|")
                if item != ""
            )
        return value

    @staticmethod
    def get_method_from_command(command):
        """choose http method based on the command name"""
        # in most cases, the first three characters of the command name are enough
        # to determine the http method
        # this list was generated from the wadl files in 8.2.0, 8.3.2, and 9.1.0
        # should work for all versions from 8.2.0 to 9.1.0 and probably others
        http_method_from_command_prefix = {
            "DELETE": ["cle", "del", "rem"],
            "GET": ["cus", "fin", "get", "isA", "isM", "log", "sea"],
            "POST": [
                "add",
                "app",
                "ass",
                "bre",
                "cle",
                "con",
                "cre",
                "dep",
                "est",
                "exc",
                "fai",
                "log",
                "mer",
                "mig",
                "qui",
                "rea",
                "rem",
                "rol",
                "sel",
                "spl",
                "ter",
                "una",
                "upl",
            ],
            "PUT": [
                "cha",
                "den",
                "edi",
                "fai",
                "imp",
                "lin",
                "mov",
                "pur",
                "rep",
                "res",
                "sha",
                "sta",
                "unl",
                "uns",
                "upd",
            ],
        }
        # this is the one exception to the above list
        prefix_to_method_exceptions = {"updateBulkUdf": "POST"}
        command_prefix = command[0:3]
        # print("command prefix: %s" % (command_prefix))
        method_from_wadl = prefix_to_method_exceptions.get(command)
        if not method_from_wadl:
            for method, prefixlist in http_method_from_command_prefix.items():
                # print("method: %s" % (method))
                # print("prefixlist: %s" % (prefixlist))
                if command_prefix in prefixlist:
                    # print("found")
                    method_from_wadl = method
                    break
        return method_from_wadl

    @staticmethod
    def argparsecommon():
        """set up common argparse arguments for BlueCat API"""
        config = argparse.ArgumentParser(
            description="BlueCat Address Manager add_DNS_Deployment_Role_list"
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
            "--configuration",
            "--cfg",
            help="BlueCat Configuration name",
            default=os.getenv("BLUECAT_CONFIGURATION"),
        )
        config.add_argument(
            "--view", help="BlueCat View", default=os.getenv("BLUECAT_VIEW")
        )
        config.add_argument(
            "--raw",
            "-r",
            default=os.getenv("BLUECAT_RAW"),
            help="set to true to not convert strings like 'name=value|...' "
            + "to dictionaries on output.  Will accept either format on input.",
        )
        config.add_argument(
            "--version", action="version", version=__progname__ + ".py " + __version__
        )
        config.add_argument(
            "--logging",
            "-l",
            help="log level, default WARNING (30),"
            + "caution: level DEBUG(10) or less "
            + "will show the password in the login call",
            default=os.getenv("BLUECAT_LOGGING", "WARNING"),
        )
        return config

    # @staticmethod
    def get_id_list(self, conn, object_ident, containerId, rangetype):
        """get object id, or a list of objects from a file"""
        obj_list = self.get_obj_list(conn, object_ident, containerId, rangetype)
        id_list = [obj.get("id") for obj in obj_list]
        return id_list

    # @staticmethod
    def get_obj_list(self, conn, object_ident, containerId, rangetype):
        """get object, or a list of objects from a file"""
        logger = logging.getLogger()
        obj = self.get_obj(conn, object_ident, containerId, rangetype)
        obj_id = obj.get("id")
        if obj_id:
            obj_list = [obj]
        else:  # not an object, must be a file name
            try:
                with open(object_ident) as f:
                    obj_list = [
                        self.get_obj(conn, line.strip(), containerId, rangetype)
                        for line in f
                        if line.strip() != ""
                    ]
            except ValueError:
                logger.info("failed to find object or open file: '%s'", object_ident)
                obj_list = []
        return obj_list

    # @staticmethod
    def get_obj(self, conn, object_ident, containerId, rangetype):
        """get an object, given an id, IP, CIDR, or range"""
        logger = logging.getLogger()
        id_pattern = re.compile(r"\d+$")
        id_match = id_pattern.match(object_ident)
        logger.info("id Match result: %s", id_match)
        if id_match:  # an id
            obj = conn.do("getEntityById", id=object_ident)
        else:  # not an id
            ip_pattern = re.compile(r"((?:\d{1,3}\.){3}\d{1,3})($|[^\d])")
            ip_match = ip_pattern.match(object_ident)
            logger.info("IP Match result: '%s'", ip_match)
            if ip_match:  # an IP
                logger.info(
                    "IP Match: '%s' and '%s'", ip_match.group(1), ip_match.group(2)
                )
                object_ident = ip_match.group(1)
                if not rangetype:
                    if ip_match.group(2) == "-":
                        rangetype = "DHCP4Range"
                    # "/" matches either IP4Block or IP4Network
                if rangetype == "IP4Address":
                    obj = conn.do(
                        "getIP4Address",
                        method="get",
                        containerId=containerId,
                        address=object_ident,
                    )
                else:
                    obj = self.get_range(conn, object_ident, containerId, rangetype)
            else:  # not and IP or id
                obj = None
        logger.info("get_obj returns %s of type %s", obj, rangetype)
        return obj

    @staticmethod
    def get_range(conn, address, containerId, rangetype):
        """get range - block, network, or dhcp range - by IPv4 or IPv6"""
        logger = logging.getLogger()
        logger.info("get_range: %s", address)
        obj = conn.do(
            "getIPRangedByIP", address=address, containerId=containerId, type=rangetype
        )
        obj_id = obj["id"]

        logging.info("getIPRangedByIP obj = %s", json.dumps(obj))
        if obj_id == 0:
            obj = None
        else:
            # bug in BlueCat - if Block and Network have the same CIDR,
            # it should return the Network, but it returns the Block.
            # So check for a matching Network.
            if rangetype == "" and obj["type"] == "IP4Block":
                cidr = obj["properties"]["CIDR"]
                network_obj = conn.do(
                    "getEntityByCIDR",
                    method="get",
                    cidr=cidr,
                    parentId=obj_id,
                    type="IP4Network",
                )
                if network_obj["id"]:
                    obj = network_obj
                    logger.info("IP4Network found: %s", obj)
        return obj

    @staticmethod
    def getinterface(server_name, configuration_id, conn):
        """get server interface object, given the server name or interface name"""
        logger = logging.getLogger()
        interface_obj_list = conn.do(
            "searchByObjectTypes",
            keyword=server_name,
            types="NetworkServerInterface",
            start=0,
            count=1000,  # same server can be in multiple Configurations
        )
        # filter for the right Configuration
        interface_ok_list = []
        for interface in interface_obj_list:
            # check the name again so that "adonis1" does not match "adonis10" etc
            name_pattern = re.compile(server_name + r"\b")
            name_match = name_pattern.match(interface["name"])
            if not name_match:
                logger.info("%s did not match %s",server_name,interface["name"])
                continue
            # check which Configuration
            server_obj = conn.do("getParent", entityId=interface["id"])
            server_configuration = conn.do("getParent", entityId=server_obj["id"])
            if server_configuration["id"] == configuration_id:
                interface_ok_list.append(interface)
        if len(interface_ok_list) > 1:
            print(
                "ERROR - more than one interface found:" #, json.dumps(interface_ok_list)
            )
            for interface in interface_obj_list:
                print(interface["name"])
            return None
        interfaceid = interface_ok_list[0]["id"]
        if interfaceid != 0:
            return interface_ok_list[0]

        # try another method, in case they gave the server display name instead
        server_obj_list = conn.do(
            "getEntitiesByName",
            parentId=configuration_id,
            name=server_name,
            type="Server",
            start=0,
            count=2,  # error if more than one
        )
        # print(json.dumps(server_obj_list))
        if len(server_obj_list) > 1:
            print(
                "ERROR - found more than one server for name",
                server_name,
                json.dumps(server_obj_list),
            )
            sys.exit(1)
        if len(server_obj_list) < 1:
            print("ERROR - server not found for", server_name)
            sys.exit(1)
        server_id = server_obj_list[0]["id"]
        if server_id == 0:
            print("ERROR - server not found for name", server_name)
            sys.exit(1)

        interface_obj_list = conn.do(
            "getEntities",
            method="get",
            parentId=server_id,
            type="NetworkServerInterface",
            start=0,
            count=1000,
        )
        if len(interface_obj_list) > 1:
            print(
                "ERROR - more than one interface found", json.dumps(interface_obj_list)
            )
            return None
        interfaceid = interface_obj_list[0]["id"]
        if interfaceid == 0:
            print("ERROR - interface not found")
            return None
        return interface_obj_list[0]
