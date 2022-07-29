#!/usr/bin/env python3

from flask import Flask
from requests import request
from requests.exceptions import JSONDecodeError
from ipaddress import ip_address, IPv4Address

from config import NETBOX_BASE_URL, NETBOX_API_TOKEN, ZONES

__author__ = "Vilhelm Prytz"
__email__ = "vilhelm@prytznet.se"


def json_request(url: str, method: str, payload={}):
    headers = {"Accept": "application/json"}

    if url.startswith(NETBOX_BASE_URL):
        headers["Authorization"] = f"Token {NETBOX_API_TOKEN}"

    r = request(method, url, json=payload, headers=headers)
    try:
        return r.json()
    except JSONDecodeError:
        raise Exception(f"{r.status_code} {r.content}")


def get_all_dns_records():
    ips = json_request(f"{NETBOX_BASE_URL}/api/ipam/ip-addresses/?limit=0", "GET")[
        "results"
    ]

    dns_names = []
    for ip in ips:
        if ip["dns_name"] == "":
            continue
        dns_names.append(
            {"dns_name": ip["dns_name"], "ip": ip["address"].split("/")[0]}
        )

    return dns_names


def get_zones(zones_config_str: str):
    return zones_config_str.split(",")


def determine_record_type(ip: str):
    """
    Determines if IP is IPv4 or IPv6 and returns 'A' or 'AAAA' respectively
    """

    return "A" if type(ip_address(ip)) is IPv4Address else "AAAA"


def write_zone_file(zone_name: str, dns_records: list):
    """
    zone_name: name of zone to write zone file for
    dns_records: list of all dns_records in Netbox, this function will filter for relevant records
    """

    zonefile = ""
    for dns_record in dns_records:
        if not dns_record["dns_name"].endswith(zone_name):
            continue
        zonefile = (
            zonefile
            + f"{dns_record['dns_name']}. IN {determine_record_type(dns_record['ip'])} {dns_record['ip']}\n"
        )

    with open(f"{zone_name}.zone", "w") as f:
        f.write(zonefile)


app = Flask(__name__)


@app.route("/")
def index():
    dns_records = get_all_dns_records()
    zones = get_zones(ZONES)

    for zone in zones:
        write_zone_file(zone, dns_records)
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0")
