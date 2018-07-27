from collections import defaultdict
import re
import logging

from netbox_netprod_importer.vendors import _AbstractVendorParser
from .constants import InterfacesRegex


logger = logging.getLogger("netbox_importer")


class CiscoParser(_AbstractVendorParser):

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

    def get_interface_type(self, interface):
        super().get_interface_type(interface)

        from pynxos.errors import CLIError
        default_type = "Other"

        cmd = "show interface {} transceiver".format(interface)

        try:
            transceiver_conf_dump = self.device.cli([cmd])[cmd]
        except CLIError:
            logger.debug("{} has no transceiver detail".format(interface))
            return "Other"

        if_type_match = re.search(
            r"type is (\S*)", transceiver_conf_dump, re.MULTILINE
        )
        if if_type_match:
            cisco_if_type = if_type_match.groups()[0]
            for pattern in InterfacesRegex:
                if re.match(pattern.value[0], cisco_if_type):
                    return pattern.value[1]

        return default_type
