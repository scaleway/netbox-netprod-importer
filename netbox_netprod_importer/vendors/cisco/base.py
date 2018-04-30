from collections import defaultdict
import re

from .constants import InterfacesRegex


class CiscoParser():
    def __init__(self, napalm_device):
        self.device = napalm_device

    def group_interfaces_by_aggreg(self, interfaces):
        port_channels = defaultdict(list)
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

            port_channels["port-channel{}".format(port_channel_id)].append(
                interface
            )

        return port_channels

    def get_interface_type(self, interface):
        interface = interface.lower()

        cmd = "show interface {} transceiver".format(interface)
        transceiver_conf_dump = self.device.cli([cmd])[cmd]

        if_type_match = re.search(
            r"type is (\S*)", transceiver_conf_dump, re.MULTILINE
        )
        if if_type_match:
            cisco_if_type = if_type_match.groups()[0]
            for pattern in InterfacesRegex:
                if re.match(pattern.value[0], cisco_if_type):
                    return pattern.value[1]

        return "Other"
