import cachetools
from collections import defaultdict
import re
import logging

from netbox_netprod_importer.vendors import _AbstractVendorParser


logger = logging.getLogger("netbox_importer")


class CiscoParser(_AbstractVendorParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cache = cachetools.TTLCache(10, 60)

    def get_interfaces_lag(self, interfaces):
        super().get_interfaces_lag(interfaces)

        interfaces_lag = defaultdict(list)
        for interface in interfaces:
            cmd = "show run interface {}".format(interface)
            interface_conf_dump = self.device.cli([cmd])[cmd]

            channel_group_match = re.search(
                r"^\s*channel-group (\S*)", interface_conf_dump, re.MULTILINE
            )
            if channel_group_match:
                port_channel_id = channel_group_match.groups()[0]
            else:
                continue

            interfaces_lag[interface] = "port-channel{}".format(
                port_channel_id
            )

        return interfaces_lag
