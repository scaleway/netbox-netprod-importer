import getpass
import logging
import socket
import sys
import argparse
from ocs.conf import get_config

from . import __appname__, __version__
from netbox_netprod_importer.poller import DevicePoller


logger = logging.getLogger("network_poller")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Poller for network devices data"
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
    for host, model in get_hosts():
        device_poller = DevicePoller(
            host, model, (parsed_args.user, passphrase)
        )
        device_poller.poll()


def get_hosts():
    yield "n9k-s101-3.dc2", "nxos"


if __name__ == "__main__":
    parse_args()
