import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import getpass
import json
import logging
import socket
import sys
import argparse
from ocs.conf import get_config
from tqdm import tqdm

from . import __appname__, __version__
from netbox_netprod_importer.lldp import build_graph_from_lldp
from netbox_netprod_importer.devices_list import parse_devices_yaml_def
from netbox_netprod_importer.push import NetboxPusher


logger = logging.getLogger("netbox_importer")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import into netbox network devices in production"
    )
    parser.add_argument(
        "devices", metavar="devices", type=str,
        help="Yaml file containing a definition of devices to poll"
    )
    parser.add_argument(
        "-u", "--user", metavar="user",
        help="user to use for connections to the devices",
        dest="user", type=str
    )
    parser.add_argument(
        "-p", "--password",
        help="ask for credentials for connections to the devices",
        dest="ask_password", action="store_true"
    )
    parser.add_argument(
        "-t", "--threads",
        help="number of threads to run",
        dest="threads", default=10, type=int
    )
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
    creds = ()
    if parsed_args.ask_password:
        creds = (parsed_args.user or getpass.getuser(), getpass.getpass())

    threads = parsed_args.threads
    importers = parse_devices_yaml_def(
        parsed_args.devices, creds
    )
    devices_props = {
        host: props for host, props in
        _multithreaded_devices_polling(importers, threads=threads)
    }

    graph = build_graph_from_lldp(importers)

    print(json.dumps({
        "devices": devices_props,
        "neighbours": {
            h: {port: [str(neighbour) for neighbour in neighbours]}
            for h, n in graph.nodes.items()
            for port, neighbours in n.neighbours.items()
        }
    }))


def _multithreaded_devices_polling(importers, threads=10):
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {}
        for host, importer in importers.items():
            future = executor.submit(_poll_and_push, host, importer)

            futures[future] = host

        futures_with_progress = tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures)
        )
        for future in futures_with_progress:
            host = futures[future]
            try:
                yield host, future.result()
            except Exception:
                logger.error("Error when polling device %s", host)


def _poll_and_push(host, importer):
    with importer:
        props = importer.poll()
        pusher = NetboxPusher(host, props)
        pusher.push()

        return props


def push(parsed_args, devices_props, graph):
    for host, props in devices_props.items():
        pusher = NetboxPusher(host, devices_props[host])
        pusher.push()


if __name__ == "__main__":
    parse_args()
