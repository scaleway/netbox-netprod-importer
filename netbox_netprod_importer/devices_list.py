import yaml

from netbox_netprod_importer.importer import DeviceImporter


def parse_devices_yaml_def(devices_yaml, creds=None):
    devices = {}
    with open(devices_yaml) as devices_yaml_str:
        for hostname, props in yaml.safe_load(devices_yaml_str).items():
            devices[hostname] = DeviceImporter(
                props.get("target") or hostname,
                napalm_driver_name=props["driver"],
                napalm_optional_args=props.get("optional_args"),
                creds=creds
            )

    return devices
