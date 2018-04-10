from collections import defaultdict
import re

from .constants import InterfacesRegex


class CiscoParser():
    def __init__(self, napalm_device):
        self.device = napalm_device

    def group_interfaces_by_aggreg(self, interfaces):
        port_channels = {}
        for interface in interfaces:
            interface_conf_dump = self.device.cli(
                "show run interface {}".format(interface)
            )

            channel_group_match = re.search(
                r"channel-group (\S*)", interface_conf_dump
            )
            if channel_group_match:
                port_channel_id = channel_group_match.groups()[0]
            else:
                continue

            port_channels["port-channel{}".format(port_channel_id)].append(
                interface
            )

    def get_interface_type(self, interface):
        interface = interface.lower()

        transceiver_conf_dump = self.device.cli(
            "show interface {} transceiver".format(interface)
        )

        if_type_match = re.search(
            r"type is (\S*)", transceiver_conf_dump
        )
        if if_type_match:
            cisco_if_type = if_type_match.groups()[0]
            for pattern in InterfacesRegex:
                if re.match(pattern.value[0], cisco_if_type):
                    return pattern.value[1]

        return "Other"
