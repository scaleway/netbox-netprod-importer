import getpass
import logging
import socket
import sys
import argparse
from ocs.conf import get_config

from . import __appname__, __version__
from netbox_netprod_importer.importer import DeviceImporter
from netbox_netprod_importer.lldp import build_graph_from_lldp


logger = logging.getLogger("netbox_importer")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import into netbox network devices in production"
    )
    parser.add_argument("user", metavar="user", type=str, help="user")
    parser.set_defaults(func=poll_datas)

    parser.add_argument(
        "--version", action="version",
        version="{} {}".format(__appname__, __version__)
    )

    arg_parser = parser
    args = arg_parser.parse_args()

    if hasattr(args, "func"):
        args.func(parsed_args=args)
    else:
        arg_parser.print_help()
        sys.exit(1)


def poll_datas(parsed_args):
    passphrase = getpass.getpass()
    hosts = list(get_hosts())
    importers = {}
    devices_props = {}
    for host, model in hosts:
        device_importer = DeviceImporter(
            host, model, (parsed_args.user, passphrase)
        )
        devices_props[host] = device_importer.poll()
        importers[host] = device_importer

    graph = build_graph_from_lldp(importers)
    import pdb; pdb.set_trace()


def get_hosts():
    yield "n9k-s101-3.dc2", "nxos"


if __name__ == "__main__":
    parse_args()
