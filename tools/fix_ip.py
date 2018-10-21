#!/usr/bin/env python3

import argparse
import ipaddress
import logging
import yaml
import sys
from netboxapi import NetboxAPI, NetboxMapper
from ocs.conf import get_config
from tqdm import tqdm


logger = logging.getLogger("netbox_importer")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Warns and tries to fix issues with IP"
    )
    subcommands = parser.add_subparsers()
    sp_orphans = subcommands.add_parser(
        "print-orphans", aliases=["po"], help=("import devices data")
    )
    sp_orphans.set_defaults(func=print_orphans)

    sp_fix_vrf = subcommands.add_parser(
        "fix-vrf", aliases=["vrf"], help=("fix associated VRF")
    )
    sp_fix_vrf.set_defaults(func=fix_vrf)

    arg_parser = parser
    args = arg_parser.parse_args()

    if hasattr(args, "func"):
        args.func(parsed_args=args)
    else:
        arg_parser.print_help()
        sys.exit(1)


def print_orphans(parsed_args):
    netbox_api = NetboxAPI(**get_config("ocs").get("netbox"))
    for p in get_orphans(netbox_api):
        print(p)


def get_orphans(netbox_api):
    ip_mapper = NetboxMapper(netbox_api, "ipam", "ip-addresses")
    prefixes_mapper = NetboxMapper(netbox_api, "ipam", "prefixes")
    missing_prefixes = set()
    for i in ip_mapper.get():
        ip_prefix = ipaddress.ip_interface(i.address).network
        if ip_prefix in missing_prefixes:
            continue

        try:
            next(prefixes_mapper.get(within_include=i.address))
        except StopIteration:
            missing_prefixes.add(ip_prefix)
            yield ip_prefix


def fix_vrf(parsed_args):
    netbox_api = NetboxAPI(**get_config("ocs").get("netbox"))
    ip_mapper = NetboxMapper(netbox_api, "ipam", "ip-addresses")
    prefixes_mapper = NetboxMapper(netbox_api, "ipam", "prefixes")
    for i in tqdm(ip_mapper.get()):
        try:
            p = next(prefixes_mapper.get(within_include=i.address))
            if p.vrf != i.vrf:
                print(i.address)
                i.vrf = p.vrf
                try:
                    i.put()
                except Exception as e:
                    logger.error("Error with IP %s", i.address)
                    logger.exception(e)
        except StopIteration:
            continue


if __name__ == "__main__":
    parse_args()
