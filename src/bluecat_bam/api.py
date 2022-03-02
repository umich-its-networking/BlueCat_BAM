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
import ipaddress
import requests


# double underscore names
__progname__ = "api"
__version__ = "0.2.7"

# python2/3 compatability
try:
    basestring
except NameError:
    basestring = str  # pylint: disable=invalid-name,redefined-builtin


class BAM(requests.Session):  # pylint: disable=R0902,R0904
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
        verify=True,
    ):
        """login to BlueCat server API, get token, set header"""
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify = verify
        self.raw = bool(raw)
        self.parentviewcache = {}  # zoneid: viewid
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
            verify=self.verify,
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
    def argparsecommon(description=""):
        """set up common argparse arguments for BlueCat API"""
        # usage: config = bluecat_bam.BAM.argparsecommon()
        config = argparse.ArgumentParser(description=description)
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

    def get_config_and_view(self, configuration_name, view_name=None):
        """get configuration_id and view_id"""
        # usage: (configuration_id, view_id) =
        #    conn.get_config_and_view(configuration_name, view_name)
        # or for just configuration:
        # (configuration_id, _) = conn.get_config_and_view(configuration_name)
        configuration_obj = self.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=configuration_name,
            type="Configuration",
        )
        configuration_id = configuration_obj["id"]

        if view_name:
            view_obj = self.do(
                "getEntityByName",
                method="get",
                parentId=configuration_id,
                name=view_name,
                type="View",
            )
            view_id = view_obj["id"]
        else:
            view_id = None
        return configuration_id, view_id

    def get_bam_api_list(self, apiname, **kwargs):
        """wrap api call with loop to handle 'start' and 'count'"""
        if not kwargs.get("count"):
            kwargs["count"] = 1000
        if not kwargs.get("start"):
            kwargs["start"] = 0
        count = kwargs["count"]
        replysize = count
        listall = []
        start = kwargs["start"]
        while replysize == count:
            kwargs["start"] = start
            listone = self.do(apiname, **kwargs)
            replysize = len(listone)
            start += replysize
            listall.extend(listone)
        return listall

    def get_id_list(self, object_ident, containerId, rangetype):
        """get object id, or a list of objects from a file"""
        obj_list = self.get_obj_list(object_ident, containerId, rangetype)
        id_list = [obj.get("id") for obj in obj_list]
        return id_list

    def get_obj_list(self, object_ident, containerId, rangetype):
        """get object, or a list of objects from a file or stdin('-')"""
        logger = logging.getLogger()
        obj_list = []
        if object_ident == "-":
            # return iterator someday ***
            with sys.stdin as f:
                obj_list = self.get_obj_lines(f, containerId, rangetype)
            # remove failed entries
            new_obj_list = [obj for obj in obj_list if obj]
            return new_obj_list
        obj, obj_type = self.get_obj(object_ident, containerId, rangetype, warn=False)
        if obj and obj.get("id"):
            obj_list = [obj]
        elif obj_type:
            print("not found", object_ident)
        else:  # not an object, must be a file name
            try:
                with open(object_ident) as f:
                    obj_list = self.get_obj_lines(f, containerId, rangetype)
                logger.info(obj_list)
                return obj_list
            except ValueError:
                logger.info("failed to find object or open file: '%s'", object_ident)
        return obj_list

    def get_obj_lines(self, fd, containerId, rangetype):
        """read lines, get obj, return obj list"""
        obj_list = []
        for line in fd:
            if line.strip() != "":
                obj, _ = self.get_obj(line.strip(), containerId, rangetype)
                if obj and obj["id"]:
                    obj_list.append(obj)
                else:
                    print("not found", line)
        return obj_list

    # pylint: disable=R0912
    def get_obj(self, object_ident, containerId, rangetype, warn=True):
        """get an object, given an id, IP, CIDR, or range,
        return object and type matched"""
        logger = logging.getLogger()
        obj_type = None
        id_pattern = re.compile(r"\d+$")
        id_match = id_pattern.match(object_ident)
        logger.info("id Match result: %s", id_match)
        pat = (
            r"^((?:\d{1,3}\.){3}\d{1,3})(?:(\/)(\d{1,2})|-((?:\d{1,3}\.){3}\d{1,3})|)$"
        )
        if id_match:  # an id
            obj = self.do("getEntityById", id=object_ident)
            obj_type = "id"
        else:  # not an id
            # ip, cidr, or range:
            # ^((?:\d{1,3}\.){3}\d{1,3})(?:(\/)(\d{1,2})|-((?:\d{1,3}\.){3}\d{1,3})|)$
            # match groups: ip, slash, prefix, range_end
            # old pattern: ((?:\d{1,3}\.){3}\d{1,3})($|[^\d])
            ip_pattern = re.compile(pat)
            ip_match = ip_pattern.match(object_ident)

            logger.info("IP Match result: '%s'", ip_match)
            if ip_match:
                if ip_match.group(3):
                    if ip_match.group(3) == "-":
                        obj_type = "DHCP4Range"
                    elif ip_match.group(3) == "/":
                        obj_type = "CIDR"  # Block or Network
                    else:
                        print("error in matching")
                else:
                    obj_type = "IP4Address"
                logger.info(
                    "IP Match: '%s' divider: '%s' prefix: '%s' range_end: '%s'",
                    ip_match.group(1),
                    ip_match.group(2),
                    ip_match.group(3),
                    ip_match.group(4),
                )
                object_ident = ip_match.group(1)
                if rangetype == "IP4Address" or (
                    rangetype is None and obj_type == "IP4Address"
                ):
                    obj = self.do(
                        "getIP4Address",
                        method="get",
                        containerId=containerId,
                        address=object_ident,
                    )
                else:
                    # get block, network, or dhcp range by ip
                    obj = self.get_range(object_ident, containerId, rangetype)
                    if obj and obj["id"]:
                        obj_type = obj["type"]
                    else:
                        obj = None
            else:  # not an IP or id
                obj = None
        logger.info("get_obj returns %s of type %s", obj, obj_type)
        if not obj and warn:
            print("Warning - no object found for:", object_ident, file=sys.stderr)
        return obj, obj_type

    def get_range(self, address, containerId, rangetype):
        """get range - block, network, or dhcp range - by IPv4 or IPv6"""
        logger = logging.getLogger()
        logger.info(
            "get_range for address: %s, containerId %s, rangetype %s",
            address,
            containerId,
            rangetype,
        )
        obj = self.do(
            "getIPRangedByIP", address=address, containerId=containerId, type=rangetype
        )
        obj_id = obj["id"]
        cidr = obj["properties"].get("CIDR")
        start = obj["properties"].get("start")

        logging.info("getIPRangedByIP obj = %s", json.dumps(obj))
        if obj_id == 0:
            obj = None
        elif start and start != address:
            obj = None
        elif cidr:
            (obj_ip, _) = cidr.split("/")
            if obj_ip != address:
                obj = None
            else:
                # bug in BlueCat - if Block and Network have the same CIDR,
                # it should return the Network, but it returns the Block.
                # So check for a matching Network.
                if rangetype == "" and obj["type"] == "IP4Block":
                    network_obj = self.do(
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

    def getinterface(self, server_name, configuration_id):
        """get server interface object, given the server name or interface name"""
        _, interface_obj = self.getserver(server_name, configuration_id)
        return interface_obj

    def getserverbyinterfacename(self, server_name, configuration_id):
        """search by server name, short or long, divided at dots"""
        # server_obj, interface_obj = conn.getserver(server_name, configuration_id)
        # assume <= 1000 servers defined  ****
        logger = logging.getLogger()
        interface_obj_list = self.do(
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
                logger.info("%s did not match %s", server_name, interface["name"])
                continue
            # check which Configuration
            server_obj = self.do("getParent", entityId=interface["id"])
            server_configuration = self.do("getParent", entityId=server_obj["id"])
            if server_configuration["id"] == configuration_id:
                interface_ok_list.append(interface)
        if len(interface_ok_list) > 1:
            print("ERROR - more than one interface found:")
            for interface in interface_ok_list:
                print(interface["name"])
            return None, None
        if interface_ok_list:
            interfaceid = interface_ok_list[0]["id"]
            if interfaceid != 0:
                return server_obj, interface_ok_list[0]
        return None, None

    def getserverbyservername(self, server_name, configuration_id):
        """get server by servername"""
        # try another method, in case they gave the server display name instead
        server_obj_list = self.do(
            "getEntitiesByNameUsingOptions",
            parentId=configuration_id,
            name=server_name,
            type="Server",
            options="ignoreCase=true",
            start=0,
            count=2,  # error if more than one
        )
        # print(json.dumps(server_obj_list))
        if len(server_obj_list) == 1:
            server_id = server_obj_list[0]["id"]
            if server_id != 0:
                interface_obj_list = self.do(
                    "getEntities",
                    method="get",
                    parentId=server_id,
                    type="NetworkServerInterface",
                    start=0,
                    count=1000,
                )
                if len(interface_obj_list) == 1:
                    interfaceid = interface_obj_list[0]["id"]
                    if interfaceid != 0:
                        return server_obj_list[0], interface_obj_list[0]
                if len(interface_obj_list) > 1:
                    print(
                        "ERROR - more than one interface found",
                        json.dumps(interface_obj_list),
                    )
        if len(server_obj_list) > 1:
            print(
                "ERROR - found more than one server for name",
                server_name,
                json.dumps(server_obj_list),
            )
        return None, None

    def getserver(self, server_name, configuration_id):
        """return server and interface objects"""
        # server_obj, interface_obj = conn.getserver(server_name, configuration_id)

        server_obj, interface_obj = self.getserverbyinterfacename(
            server_name, configuration_id
        )
        if not server_obj:
            server_obj, interface_obj = self.getserverbyservername(
                server_name, configuration_id
            )
        if not server_obj:
            print("ERROR - server or interface not found for", server_name)
        return server_obj, interface_obj

    def get_zone(self, domain_name, view_id):
        """get closest zone for domain_name"""
        logger = logging.getLogger()
        domain_label_list = domain_name.split(".")
        logger.info(domain_label_list)
        zone_end = len(domain_label_list)
        zone_start = zone_end - 1
        search_domain = ".".join(domain_label_list[zone_start:zone_end])
        current_domain = ""
        parent_id = view_id

        while True:
            logger.info(
                "start: %s, end: %s, search: %s", zone_start, zone_end, search_domain
            )
            zone = self.do(
                "getEntityByName",
                method="get",
                parentId=parent_id,
                name=search_domain,
                type="Zone",
            )
            if zone.get("id") == 0:  # try same parent, dotted name
                if zone_start > 0:
                    zone_start -= 1  # decrement by one
                    search_domain = ".".join(domain_label_list[zone_start:zone_end])
                    continue
                break
            found_zone = zone
            parent_id = zone.get("id")
            current_domain = ".".join(domain_label_list[zone_start:])
            logger.info("current_domain: %s, zone: %s", current_domain, zone)
            if zone_start != 0:
                zone_end = zone_start
                zone_start -= 1
                search_domain = ".".join(domain_label_list[zone_start:zone_end])
            else:
                search_domain = ""
                break
        remainder = ".".join(domain_label_list[0:zone_end])
        logger.info("remainder: %s", remainder)
        return found_zone, remainder

    def get_fqdn(self, domain_name, view_id, record_type="HostRecord"):
        """get list of entities with given fqdn and type"""
        logger = logging.getLogger()
        zone, remainder = self.get_zone(domain_name, view_id)
        if record_type.lower() == "zone":
            entities = [zone]
        else:
            entities = self.do(
                "getEntitiesByNameUsingOptions",
                method="get",
                parentId=zone["id"],
                name=remainder,
                type=record_type,
                options="ignoreCase=true",
                start=0,
                count=1000,
            )
        logger.info("entities: %s", entities)
        return entities

    def delete_ip_obj(self, ip_obj):
        """delete ip obj, handle case of DHCP_ALLOCATED"""
        ip_id = ip_obj["id"]
        if ip_obj["properties"]["state"] == "DHCP_ALLOCATED":
            # change to dhcp reserved with a fake mac address, then delete
            # use random self-assigned mac address like fedcba987654
            # in case the existing mac already has a dhcp reserved entry
            result = self.do(
                "changeStateIP4Address",
                addressId=ip_id,
                targetState="MAKE_DHCP_RESERVED",
                macAddress="fedcba987654",
            )
            if result:
                return result
        result = self.do(
            "deleteWithOptions",
            method="delete",
            objectId=ip_id,
            options="noServerUpdate=true|deleteOrphanedIPAddresses=true|",
        )
        return result

    def get_dhcp_ranges(self, networkid):
        """get list of ranges"""
        logger = logging.getLogger()
        range_list = self.get_bam_api_list(
            "getEntities",
            parentId=networkid,
            type="DHCP4Range",
        )
        logger.debug(range_list)
        return range_list

    @staticmethod
    def make_dhcp_ranges_list(range_list):
        """return sorted list of dict with the start and end ipaddress class IP objects
        and the BlueCat range object, like:
        [
            { "start": start_ip_obj, "end": end_ip_obj, "range": range_obj }
            ...
        ]"""
        logger = logging.getLogger()
        range_info_list = []
        for dhcp_range in range_list:
            start = ipaddress.ip_address(dhcp_range["properties"]["start"])
            end = ipaddress.ip_address(dhcp_range["properties"]["end"])
            range_info_list.append({"start": start, "end": end, "range": dhcp_range})
        logger.info(range_info_list)
        range_info_list.sort(key=lambda self: self["start"])
        return range_info_list

    def getparentview(self, entity_id):
        """walk tree up to view, with cache"""
        view_id = self.parentviewcache.get("id")
        if view_id:
            return view_id
        parent = self.do("getParent", entityId=entity_id)
        if parent == 0:
            print("ERROR - got to top without finding a view for object id", entity_id)
            return None
        entity_type = parent["type"]
        if entity_type == "View":
            view_id = parent["id"]
            self.parentviewcache[entity_id] = view_id
            return view_id
        return self.getparentview(parent["id"])  # recursive

    def get_ip_list(self, networkid, states=None):
        """get [filtered] list of IP entities"""
        ip_list = self.get_bam_api_list(
            "getEntities",
            parentId=networkid,
            type="IP4Address",
        )
        if states:
            ip_list = [ip for ip in ip_list if ip["properties"]["state"] in states]
        return ip_list

    @staticmethod
    def make_ip_dict(ip_list):
        """convert ip_list to dict: {ipaddress_class_obj: ip_entity}"""
        ip_dict = {
            ipaddress.ip_address(ip_obj["properties"]["address"]): ip_obj
            for ip_obj in ip_list
        }
        return ip_dict

    def get_shared_network_tag_by_name(self, name, configuration_id):
        """get shared network tag by name, in configuration"""
        logger = logging.getLogger()
        cfg_obj = self.do("getEntityById", id=configuration_id)
        shared_net_group_id = int(cfg_obj["properties"]["sharedNetwork"])
        # search for name
        obj_list = self.get_bam_api_list(
            "searchByObjectTypes",
            keyword=name,
            types="Tag,TagGroup",
        )
        found = None  # define in this scope
        for obj in obj_list:
            # verify exact name match (not partial)
            if obj["name"] == name:
                # verify that it is a shared_network tag for this configuration
                group = self.find_parent_of_type(obj["id"], "TagGroup")
                logger.info(
                    "compare %s to %s",
                    json.dumps(group["id"]),
                    json.dumps(shared_net_group_id),
                )
                if group["id"] == shared_net_group_id:
                    found = obj
                    logger.info("found %s", found)
        return found

    def find_parent_of_type(self, obj_id, obj_type):
        """search up tree for parent with the given type,
        like finding the group for a tag,
        or the configuration for a network,
        or the view for a zone or record,
        returns parent object"""
        logger = logging.getLogger()
        myid = obj_id
        mytype = None
        parent_obj = None  # make it in this scope
        while mytype != obj_type and myid != 0:
            parent_obj = self.do("getParent", entityId=myid)
            mytype = parent_obj["type"]
            myid = parent_obj["id"]
            logger.info("id: %s, name: %s, type: %s", myid, parent_obj["name"], mytype)
        if myid == 0:
            return None
        return parent_obj


class DhcpRangeList(list):  # pylint: disable=R0902
    """make a dhcp range list object, with function to check if in range,
    list must be in format from make_dhcp_ranges_list"""

    def __init__(
        self,
        dhcp_ranges_list,  # sorted list with start/end from make_dhcp_ranges_list
        network_obj,
    ):
        """DHCP range list, with extra functions"""
        list.__init__(self, BAM.make_dhcp_ranges_list(dhcp_ranges_list))
        # save network, range list, and current range
        self.network_obj = network_obj
        self.ranges = dhcp_ranges_list
        self.range_num = 0
        # calculate network start/end
        self.cidr = network_obj["properties"]["CIDR"]
        self.network_net = ipaddress.IPv4Network(self.cidr)
        self.network_ip = self.network_net.network_address
        self.broadcast_ip = self.network_net.broadcast_address
        # start with gap from network_ip to before first range
        self.gap = self.network_ip
        if self.__len__() > 0:
            # range list must be sorted
            self.start = self[0]["start"]
            self.end = self[0]["end"]
        else:
            # no range_size, put start after end so it never matches
            self.start = self.broadcast_ip + 1
            self.end = self.broadcast_ip

    def in_range(self, ip):
        """check if given IP is in any of the DHCP raanges"""
        # note that this is most efficient if IP's are checked in ascending order
        if ip < self.gap:
            # restart range search
            self.range_num = 0
        elif ip < self.start:
            return False
        elif ip < self.end:
            return True
        else:
            self.range_num += 1
        # outside network?
        if ip < self.network_ip or ip > self.broadcast_ip:
            return False
        # search ranges
        while self.range_num < self.__len__():
            if ip <= self[self.range_num]["end"]:
                if ip >= self[self.range_num]["start"]:
                    return True
                return False
            # move to next range
            self.range_num += 1
        return False
