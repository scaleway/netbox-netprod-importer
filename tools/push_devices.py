#!/usr/bin/env python3

import getpass
import json
import logging
import socket
import sys
import argparse
from boltons.cacheutils import LRU
from netboxapi import NetboxAPI, NetboxMapper
from ocs.conf import get_config
import yaml


def parse_args():
    parser = argparse.ArgumentParser(
        description="Push devices and models to netbox"
    )
    parser.add_argument(
        "devices", metavar="devices", type=str,
        help="Yaml file containing a definition of devices to poll"
    )
    parser.add_argument(
        "--types", metavar="device_types",
        type=str, help="Yaml file containing a definition of device types"
    )
    parser.set_defaults(func=push_devices)

    arg_parser = parser
    args = arg_parser.parse_args()

    if hasattr(args, "func"):
        args.func(parsed_args=args)
    else:
        arg_parser.print_help()
        sys.exit(1)


def push_devices(parsed_args):
    netbox_api = NetboxAPI(**get_config("ocs").get("netbox"))
    manufacturers = create_manufacturers(netbox_api)

    if parsed_args.types:
        create_device_types(
            netbox_api, parse_yaml_file(parsed_args.types),
            manufacturers
        )

    create_devices(netbox_api, parse_yaml_file(parsed_args.devices))


def parse_yaml_file(yaml_file):
    with open(yaml_file) as yaml_str:
        return yaml.safe_load(yaml_str)


def create_manufacturers(netbox_api):
    mapper = NetboxMapper(netbox_api, "dcim", "manufacturers")
    manufacturers = {}

    for name in ("Cisco", "Juniper"):
        try:
            manufacturer = next(mapper.get(slug=name.lower()))
        except StopIteration:
            manufacturer = mapper.post(name=name, slug=name.lower())

        manufacturers[name.lower()] = manufacturer

    return manufacturers


def create_devices(netbox_api, devices):
    device_types_mapper = NetboxMapper(netbox_api, "dcim", "device-types")
    device_types = LRU(
        on_miss=lambda slug: next(device_types_mapper.get(slug=slug))
    )

    device_mapper = NetboxMapper(netbox_api, "dcim", "devices")
    for name, props in devices.items():
        device_type = props.pop("model")

        try:
            device = next(device_mapper.get(slug=name.lower()))
        except StopIteration:
            # XXX: find a way to classify devices by roles
            device = device_mapper.post(
                name=name, slug=name.lower(),
                device_type=device_types[device_type.lower()],
                device_role=1,
                site=1,
            )

        update_netbox_obj_from(device, props)
        device.put()


def create_device_types(netbox_api, types, manufacturers):
    mapper = NetboxMapper(netbox_api, "dcim", "device-types")
    for name, props in types.items():
        manufacturer_name = props.pop("manufacturer")

        try:
            t = next(mapper.get(slug=name.lower()))
        except StopIteration:
            t = mapper.post(
                model=name, slug=name.lower(),
                manufacturer=manufacturers[manufacturer_name]
            )

        update_netbox_obj_from(t, props)
        # Until issue #2272 is fixed on netbox
        t.__upstream_attrs__.remove("subdevice_role")
        t.put()

        create_device_type_interfaces(netbox_api, t, props["ports"])


def create_device_type_interfaces(netbox_api, device_type, ports):
    mapper = NetboxMapper(netbox_api, "dcim", "interface-templates")

    for port_type, nb in ports.items():
        if nb > 1:
            port_names = (
                "{}/{}".format(port_type, i) for i in range(1, nb + 1)
            )
        else:
            port_names = (port_type, )

        upstream_ports = {
            p.name for p in mapper.get(devicetype_id=device_type)
        }
        for name in port_names:
            if name not in upstream_ports:
                mapper.post(name=name, device_type=device_type)


def update_netbox_obj_from(netbox_obj, values):
    for k, v in values.items():
        setattr(netbox_obj, k, v)

    return netbox_obj


if __name__ == "__main__":
    parse_args()
