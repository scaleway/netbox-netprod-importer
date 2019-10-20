import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import getpass
import json
import logging
import socket
import sys
import argparse
from netboxapi import NetboxAPI
from tqdm import tqdm

from . import __appname__, __version__
from netbox_netprod_importer.config import get_config, load_config
from netbox_netprod_importer.devices_list import parse_devices_yaml_def
from netbox_netprod_importer.devices_list import parse_filter_yaml_def
from netbox_netprod_importer.push import (
    NetboxDevicePropsPusher, NetboxInterconnectionsPusher
)


logger = logging.getLogger("netbox_importer")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import into netbox network devices in production"
    )
    subcommands = parser.add_subparsers()

    sp_import = subcommands.add_parser(
        "import", aliases=["imp"], help=("import devices data")
    )
    sp_import.set_defaults(func=import_data)

    sp_interconnect = subcommands.add_parser(
        "interconnect", aliases=["interco"], help=("interconnect devices")
    )
    sp_interconnect.set_defaults(func=interconnect)

    sp_inventory = subcommands.add_parser(
        "inventory", aliases=["inv"],
        help=("inventory devices (import + interconnect)")
    )
    sp_inventory.set_defaults(func=inventory)

    for sp in (sp_import, sp_interconnect, sp_inventory):
        sp.add_argument(
            "-f", "--file", metavar="DEVICES",
            help="Yaml file containing a definition of devices to poll",
            dest="devices", type=str
        )
        sp.add_argument(
            "-F", "--filter", metavar="FILTER",
            help="Yaml file containing filter selection from netbox devices for polling",
            dest="filter", type=str
        )
        sp.add_argument(
            "-u", "--user", metavar="USER",
            help="user to use for connections to the devices",
            dest="user", type=str
        )
        sp.add_argument(
            "-p", "--password",
            help="ask for credentials for connections to the devices",
            dest="ask_password", action="store_true"
        )
        sp.add_argument(
            "-P", "--Password", metavar="PASSWORD",
            help="credentials for connections to the devices",
            dest="password", type=str
        )
        sp.add_argument(
            "-t", "--threads", metavar="THREADS",
            help="number of threads to run",
            dest="threads", default=10, type=int
        )
        sp.add_argument(
            "--overwrite",
            help="overwrite data already pushed",
            dest="overwrite", action="store_true"
        )
        sp.add_argument(
            "-v", "--verbose", metavar="LEVEL",
            help="enable debug or warning, verbose output",
            dest="verbose"
        )

    parser.add_argument(
        "--version", action="version",
        version="{} {}".format(__appname__, __version__)
    )

    arg_parser = parser
    args = arg_parser.parse_args()

    if hasattr(args, "func"):
        try:
            load_config()
        except FileNotFoundError:
            sys.exit(2)

        if args.verbose:
            numeric_level = getattr(logging, args.verbose.upper(), None)
            if not isinstance(numeric_level, int):
                raise ValueError('Invalid log level: %s' % args.verbose)
            logging.getLogger().setLevel(numeric_level)

        args.creds = _get_creds(args)
        print("Initializing importers…")
        if args.devices:
            args.importers = parse_devices_yaml_def(
                args.devices, args.creds
            )
        elif args.filter:
            args.importers = parse_filter_yaml_def(
                args.filter, args.creds
            )
        else:
            arg_parser.error("Device file or filter file required")

        args.func(parsed_args=args)
    else:
        arg_parser.print_help()
        sys.exit(1)

def inventory(parsed_args):
    import_data(parsed_args)
    interconnect(parsed_args)

def import_data(parsed_args):
    print("Fetching and pushing data…")
    for host, props in _multithreaded_devices_polling(
            importers=parsed_args.importers,
            threads=parsed_args.threads,
            overwrite=parsed_args.overwrite
    ):
        continue


def _get_creds(parsed_args):
    creds = ()
    if parsed_args.ask_password:
        creds = (parsed_args.user or getpass.getuser(), getpass.getpass())
    elif parsed_args.password:
        creds = (parsed_args.user or getpass.getuser(), parsed_args.password)

    return creds


def _multithreaded_devices_polling(importers, threads=10, overwrite=False):
    importers = importers.copy()
    netbox_api = NetboxAPI(**get_config()["netbox"])
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {}
        for host, importer in importers.items():
            future = executor.submit(
                _poll_and_push, netbox_api, host, importer, overwrite
            )

            futures[future] = host

        futures_with_progress = tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures)
        )
        for future in futures_with_progress:
            host = futures[future]
            try:
                yield host, future.result()
                importers.pop(host)
            except Exception as e:
                logger.error("Error when polling device %s: %s", host, e)


def _poll_and_push(netbox_api, host, importer, overwrite):
    with importer:
        props = importer.poll()
        pusher = NetboxDevicePropsPusher(
            netbox_api, host, props, overwrite=overwrite
        )
        pusher.push()

        return props


def interconnect(parsed_args):
    netbox_api = NetboxAPI(**get_config()["netbox"])
    remove_domains = get_config().get("remove_domains")

    interco_pusher = NetboxInterconnectionsPusher(
        netbox_api, remove_domains=remove_domains
    )

    print("Finding neighbours and interconnecting…")
    interco_result = interco_pusher.push(
        importers=parsed_args.importers,
        threads=parsed_args.threads,
        overwrite=parsed_args.overwrite
    )
    print("{} interconnection(s) applied".format(interco_result["done"]))
    if interco_result["errors_device"]:
        logger.error(
            "Error getting neighbours on %s device(s)",
            interco_result["errors_device"]
        )
    if interco_result["errors_interco"]:
        logger.error(
            "Error pushing %s interconnection(s)",
            interco_result["errors_interco"]
        )


if __name__ == "__main__":
    parse_args()
