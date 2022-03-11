#!/usr/bin/env python

"""add_update_get_delete_urllib_class.py"""

# to be python2/3 compatible:
from __future__ import print_function

# from builtins import str

import os
import sys
import json
import argparse
import logging

import urllib.request

from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request


class BAM:  # pylint: disable=R0902
    """BAM API using urllib"""

    def __init__(
        self,
        server,
        username,
        password,
        raw=False,
        raw_in=False,
        timeout=None,
        verify=True,
    ):
        """login to BlueCat server API, get token, set header"""
        super().__init__()
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
            raise ValueError
        self.mainurl = self.convert_url(server)
        logging.info("url: %s", self.mainurl)

        self.login()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.logout()

    @staticmethod
    def request(method, url, data=None, params=None, headers=None, timeout=10):
        """try to mimic the requests module"""
        logger = logging.getLogger()
        logger.info("method %s url %s params %s", method, url, params)
        if headers is None:
            headers = {}
        if params:
            params = urllib.parse.urlencode(params)
            url = "%s%s" % (url, params)
        if data:
            data = data.encode("utf-8")  # converts utf-8 to bytes
        request = Request(url, headers=headers, data=data, method=method)
        try:
            # bandit blacklists urlopen because it can open files also
            # that is not a concern here
            with urlopen(request, timeout=timeout) as response:  # nosec
                logger.debug(response.status)
                result = response.read()
                logger.debug(result)
                if response.status != 200:
                    print(response.status)
                    return response.status
                if len(result) > 0:
                    return json.loads(result)
                return None
        except HTTPError as error:
            print(error.status, error.reason)
            raise HTTPError from error
        except URLError as error:
            print(error.reason)
            raise URLError from error
        except TimeoutError as error:
            print("Request timed out")
            raise TimeoutError from error
        return None

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
        logging.info("mainurl in login %s", self.mainurl)
        url = self.mainurl + "login?"
        logging.info("url %s", url)
        response = self.request(
            "GET",
            url,
            params={"username": self.username, "password": self.password},
        )
        logging.info("response %s", response)
        self.token = str(response)
        self.token = self.token.split()[2] + " " + self.token.split()[3]
        self.token_header = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    def logout(self):
        """log out of BlueCat server, return nothing"""
        self.request("GET", self.mainurl + "logout?", headers=self.token_header)

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
            headers=self.token_header,
            data=data,
            params=kwargs,
            timeout=self.timeout,
            # verify=self.verify,
        )
        # logging.info(vars(response.request))
        logging.info("api response %s", response)
        # logging.debug(response.status)
        # logging.info("response: %s", response.read())
        # logging.debug("headers: %s", response.headers)
        # logging.debug("len: %s", response.headers.get("Content-Length"))
        # print("status_code: %s" % response.status_code)
        # if response.status_code != 200:
        #    print(response.text, file=sys.stderr)
        # response.raise_for_status()
        # check type of response
        logging.info(response)
        # if response.headers.get("Content-Length") == "0":
        if isinstance(response, str) and len(response) == 0:
            obj = None  # void (null) response
        else:
            # obj = response.json()
            obj = response
        if not self.raw:
            obj = self.convert_response(obj)
        return obj
        # pylint: enable=invalid-name,R0912

    @staticmethod
    def convert_dict_in_str_to_dict(data):
        """data, properties, and overrides can be dict, but passed as json string,
        especially from cli"""
        if data and isinstance(data, str) and data[0] == "{":
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
            if isinstance(data, str):
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
        elif isinstance(obj, str):
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
        if isinstance(value, str) and "|" in value:
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


def main():
    """add_update_get_delete"""
    # test data
    mac_address = "02-00-02-00-02-00"  # in the user defined range

    config = argparse.ArgumentParser(description="add next dhcp reserved")
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
        "--logging",
        "-l",
        help="log level, default WARNING (30),"
        + "caution: level DEBUG(10) or less will show the password in the login call",
        default=os.getenv("BLUECAT_LOGGING", "WARNING"),
    )
    args = config.parse_args()

    add_update_get_delete(args, mac_address)


def add_update_get_delete(args, mac_address):
    """add_update_get_delete demo code"""
    logger = logging.getLogger()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    logger.setLevel(args.logging)

    # with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
    with BAM(args.server, args.username, args.password) as conn:

        configuration_obj = conn.do(
            "getEntityByName",
            method="get",
            parentId=0,
            name=args.configuration,
            type="Configuration",
        )

        config_id = configuration_obj["id"]

        print("check if mac address exists, should get id=0 if not")
        oldmac = conn.do(
            "getMACAddress",
            method="get",
            configurationId=config_id,
            macAddress=mac_address,
        )
        print("old mac is: ", json.dumps(oldmac))
        mac_id = oldmac["id"]
        print("id: ", mac_id)
        if mac_id != 0:
            print("ERROR - mac address already exists")
            sys.exit(1)
        print()

        print("add new mac address, response is the id of the new entity")
        mac_id = conn.do(
            "addMACAddress",
            method="post",
            configurationId=config_id,
            macAddress=mac_address,
            properties="",
        )
        print("new id is: ", mac_id)
        print()

        print("get mac address just added")
        entity = conn.do(
            "getMACAddress",
            method="get",
            configurationId=config_id,
            macAddress=mac_address,
        )
        print(json.dumps(entity))
        print()

        print("change name in local copy of the mac address")
        entity["name"] = "testmac"
        print(json.dumps(entity))
        print()

        print("update the mac address in bluecat, expect null response")
        resp = conn.do("update", method="PUT", body=entity)
        print(json.dumps(resp))
        print()

        print("get mac address from bluecat")
        entity = conn.do(
            "getMACAddress",
            method="get",
            configurationId=config_id,
            macAddress=mac_address,
        )
        print(json.dumps(entity))
        print()

        print("delete mac address, expect null response")
        resp = conn.do("delete", method="delete", objectId=mac_id)
        print(json.dumps(resp))
        print()

        print("check if mac address exists, should get id=0")
        entity = conn.do(
            "getMACAddress",
            method="get",
            configurationId=config_id,
            macAddress=mac_address,
        )
        print(json.dumps(entity))
        print()

        # logout is automatic with context manager
        print("done")


if __name__ == "__main__":
    main()
