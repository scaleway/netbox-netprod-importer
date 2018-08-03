import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import logging
import napalm
from tqdm import tqdm
import yaml

from netbox_netprod_importer.importer import DeviceImporter


logger = logging.getLogger("netbox_importer")


def parse_devices_yaml_def(devices_yaml, creds=None, threads=10):
    devices = {}
    with open(devices_yaml) as devices_yaml_str:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {}
            for hostname, props in yaml.safe_load(devices_yaml_str).items():
                future = executor.submit(
                    DeviceImporter,
                    props.get("target") or hostname,
                    napalm_driver_name=props["driver"],
                    napalm_optional_args=props.get("optional_args"),
                    creds=creds
                )
                futures[future] = hostname

            futures_with_progress = tqdm(
                concurrent.futures.as_completed(futures),
                total=len(futures)
            )
            for future in futures_with_progress:
                try:
                    devices[futures[future]] = future.result()
                except Exception as e:
                    logger.error(
                        "Cannot connect to device %s: %s", hostname, e
                    )
    return devices
