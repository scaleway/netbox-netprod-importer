import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import logging
import napalm
from tqdm import tqdm
import yaml

from netbox_netprod_importer.importer import DeviceImporter


logger = logging.getLogger("netbox_importer")


def parse_devices_yaml_def(devices_yaml, creds=None):
    devices = {}
    with open(devices_yaml) as devices_yaml_str:
        devices = {}
        for hostname, props in tqdm(yaml.safe_load(devices_yaml_str).items()):
            try:
                devices[hostname] = DeviceImporter(
                    props.get("target") or hostname,
                    napalm_driver_name=props["driver"],
                    napalm_optional_args=props.get("optional_args"),
                    creds=creds
                )
            except Exception as e:
                logger.error(
                    "Cannot connect to device %s: %s", hostname, e
                )
    return devices
