"""test_api_dhcp_ranges"""  # pylint requires docstring
import ipaddress

# import pytest
import bluecat_bam

# from bluecat_bam.cli import main


def test_make_dhcp_ranges_list():
    """make_dhcp_ranges_list"""
    network_obj = {
        "id": 10490777,
        "name": "V-BLUECAT-TEST-2",
        "type": "IP4Network",
        "properties": {
            "CIDR": "10.213.152.224/27",
            "gateway": "10.213.152.225",
            "defaultView": "1048598",
        },
    }
    range_list = [
        {
            "id": 17254380,
            "name": "test2-unreg",
            "type": "DHCP4Range",
            "properties": {"start": "10.213.152.230", "end": "10.213.152.240"},
        },
        {
            "id": 22655002,
            "name": None,
            "type": "DHCP4Range",
            "properties": {"start": "10.213.152.250", "end": "10.213.152.254"},
        },
        {
            "id": 22655003,
            "name": None,
            "type": "DHCP4Range",
            "properties": {"start": "10.213.152.241", "end": "10.213.152.245"},
        },
    ]

    dhcp_ranges_list = bluecat_bam.DhcpRangeList(range_list, network_obj)

    expected = [
        {
            "start": ipaddress.ip_address("10.213.152.230"),
            "end": ipaddress.ip_address("10.213.152.240"),
            "range": {
                "id": 17254380,
                "name": "test2-unreg",
                "type": "DHCP4Range",
                "properties": {"start": "10.213.152.230", "end": "10.213.152.240"},
            },
        },
        {
            "start": ipaddress.ip_address("10.213.152.241"),
            "end": ipaddress.ip_address("10.213.152.245"),
            "range": {
                "id": 22655003,
                "name": None,
                "type": "DHCP4Range",
                "properties": {"start": "10.213.152.241", "end": "10.213.152.245"},
            },
        },
        {
            "start": ipaddress.ip_address("10.213.152.250"),
            "end": ipaddress.ip_address("10.213.152.254"),
            "range": {
                "id": 22655002,
                "name": None,
                "type": "DHCP4Range",
                "properties": {"start": "10.213.152.250", "end": "10.213.152.254"},
            },
        },
    ]

    assert dhcp_ranges_list == expected
