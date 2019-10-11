import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import logging
import napalm
from tqdm import tqdm
import yaml

from netbox_netprod_importer.importer import DeviceImporter

from netboxapi import NetboxAPI
from netbox_netprod_importer.config import get_config

logger = logging.getLogger("netbox_importer")


def parse_devices_yaml_def(devices_yaml, creds=None):
    devices = {}
    with open(devices_yaml) as devices_yaml_str:
        for hostname, props in tqdm(yaml.safe_load(devices_yaml_str).items()):
            try:
                devices[hostname] = DeviceImporter(
                    props.get("target") or hostname,
                    napalm_driver_name=props["driver"],
                    napalm_optional_args=props.get("optional_args"),
                    creds=creds,
                    discovery_protocol=props.get("discovery_protocol")
                )
            except Exception as e:
                logger.error(
                    "Cannot connect to device %s: %s", hostname, e
                )
    return devices


def parse_filter_yaml_def(filter_yaml, creds=None):
    netbox_api = NetboxAPI(**get_config()["netbox"])
    devices = {}
    with open(filter_yaml) as filter_yaml_str:
        yml = yaml.safe_load(filter_yaml_str)
        platforms_js = netbox_api.get("dcim/platforms")
        platforms = {}
        for platform in platforms_js["results"]:
            if platform["napalm_driver"]:
                if platform["napalm_driver"]:
                    platforms[platform["id"]] = {
                        "napalm_driver": platform["napalm_driver"],
                        "napalm_args": platform["napalm_args"]
                    }
        if not platforms:
            raise Exception("Not for one platform napalm_driver is not "
                            "defined")

        devlist = netbox_api.get("dcim/devices/", params=yml["filter"])
        for device in devlist["results"]:
            if not device.get("platform") or \
                    not platforms.get(device["platform"]["id"]):
                continue

            try:
                if device["primary_ip"].get("address"):
                    dev = device["primary_ip"].get("address").split("/")[0]
                else:
                    dev = device["name"]
                devices[device["name"]] = DeviceImporter(
                    dev,
                    napalm_driver_name=platforms[
                         device["platform"]["id"]
                    ]["napalm_driver"],
                    napalm_optional_args=platforms[
                        device["platform"]["id"]
                    ]["napalm_args"],
                    creds=creds,
                    discovery_protocol=yml["discovery_protocol"].get(
                        platforms[device["platform"]["id"]]
                    )
                )
            except Exception as e:
                logger.error(
                    "Cannot connect to device %s: %s", device["name"], e
                )
    return devices
