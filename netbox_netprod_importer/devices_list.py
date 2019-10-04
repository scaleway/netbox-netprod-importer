import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import logging
import napalm
from tqdm import tqdm
import yaml
import sys

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
        q_list = []
        yml = yaml.safe_load(filter_yaml_str)
        for fil, props in tqdm(yml["filter"].items()):
            if props is not None:
                if type(props) is list:
                    q_list.append(fil + "=" +
                                  ("&" + fil + "=").join(str(x) for x in props)
                                  )
                else:
                    q_list.append(fil + "=" + str(props))
        logger.info("Resultant filter %s", "&".join(q_list))
        platforms_js = netbox_api.get("dcim/platforms")
        platforms = {}
        platforms_args = {}
        for platform in platforms_js["results"]:
            if platform["napalm_driver"]:
                platforms[platform["id"]] = platform["napalm_driver"]
                platforms_args[platform["id"]] = platform["napalm_args"]
        if len(platforms) == 0:
            logger.error("Not for one platform napalm_driver is not defined")
            sys.exit(4)

        devlist = netbox_api.get("dcim/devices/?" + "&".join(q_list))
        for device in devlist["results"]:
            if not device["platform"]:
                continue
            if not platforms.get(device["platform"]["id"]):
                continue

            try:
                devices[device["name"]] = DeviceImporter(
                    device["primary_ip"].get("address").split("/")[0]
                    or device["name"],
                    napalm_driver_name=platforms[device["platform"]["id"]],
                    napalm_optional_args=platforms_args[
                        device["platform"]["id"]
                    ],
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
