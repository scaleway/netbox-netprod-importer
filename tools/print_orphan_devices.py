#!/usr/bin/env python3

import argparse
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import sys
from netboxapi import NetboxAPI, NetboxMapper
from ocs.conf import get_config
import tqdm


def parse_args():
    parser = argparse.ArgumentParser(
        description="Print devices that are not connected to anything"
    )
    parser.add_argument(
        "--device-role",
        help="device role to filter",
        dest="device_role_id", type=int
    )
    parser.add_argument(
        "--threads",
        help="number of threads to run",
        dest="threads", default=10, type=int
    )
    parser.set_defaults(func=print_orphans)

    arg_parser = parser
    args = arg_parser.parse_args()

    if hasattr(args, "func"):
        args.func(parsed_args=args)
    else:
        arg_parser.print_help()
        sys.exit(1)


def print_orphans(parsed_args):
    netbox_api = NetboxAPI(**get_config("ocs").get("netbox"))
    devices_mapper = NetboxMapper(netbox_api, "dcim", "devices")

    threads = parsed_args.threads
    if parsed_args.device_role_id:
        iter_devices = devices_mapper.get(
            role_id=parsed_args.device_role_id, limit=threads
        )
    else:
        iter_devices = devices_mapper.get(limit=threads)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {}
        for d in tqdm.tqdm(iter_devices):
            future = executor.submit(
                connection_present_for_device, d, netbox_api
            )
            futures[future] = d

        for f in concurrent.futures.as_completed(futures):
            if not f.result():
                print(futures[f].name)


def connection_present_for_device(device, netbox_api):
    mapper = NetboxMapper(netbox_api, "dcim", "interface-connections")
    try:
        next(mapper.get(device=device.name))
        return True
    except StopIteration:
        return False


if __name__ == "__main__":
    parse_args()
