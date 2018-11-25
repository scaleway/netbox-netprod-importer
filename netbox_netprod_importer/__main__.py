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
    sp_import.add_argument(
        "--overwrite",
        help="overwrite devices already pushed",
        dest="overwrite", action="store_true"
    )
    sp_import.set_defaults(func=import_data)

    sp_interconnect = subcommands.add_parser(
        "interconnect", aliases=["interco"], help=("interconnect devices")
    )
    sp_interconnect.set_defaults(func=interconnect)

    for sp in (sp_import, sp_interconnect):
        sp.add_argument(
            "devices", metavar="DEVICES", type=str,
            help="Yaml file containing a definition of devices to poll"
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
            "-t", "--threads", metavar="THREADS",
            help="number of threads to run",
            dest="threads", default=10, type=int
        )
        sp.add_argument(
            "-d", "--debug", help="enable debug, verbose output",
            dest="debug", action="store_true"
        )

    parser.add_argument(
        "--version", action="version",
        version="{} {}".format(__appname__, __version__)
    )

    arg_parser = parser
    args = arg_parser.parse_args()

    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s"
        )

    if hasattr(args, "func"):
        try:
            load_config()
        except FileNotFoundError:
            sys.exit(2)
        args.func(parsed_args=args)
    else:
        arg_parser.print_help()
        sys.exit(1)


def import_data(parsed_args):
    creds = _get_creds(parsed_args)
    threads = parsed_args.threads

    print("Initializing importers…")
    importers = parse_devices_yaml_def(parsed_args.devices, creds)
    print()

    print("Fetching and pushing data…")
    for host, props in _multithreaded_devices_polling(
            importers=importers, threads=threads,
            overwrite=parsed_args.overwrite
    ):
        continue


def _get_creds(parsed_args):
    creds = ()
    if parsed_args.ask_password:
        creds = (parsed_args.user or getpass.getuser(), getpass.getpass())

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
    creds = _get_creds(parsed_args)
    threads = parsed_args.threads
    netbox_api = NetboxAPI(**get_config()["netbox"])

    interco_pusher = NetboxInterconnectionsPusher(netbox_api)

    print("Initializing importers…")
    importers = parse_devices_yaml_def(parsed_args.devices, creds)
    print()

    print("Finding neighbours and interconnecting…")
    interco_result = interco_pusher.push(importers=importers, threads=threads)
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
