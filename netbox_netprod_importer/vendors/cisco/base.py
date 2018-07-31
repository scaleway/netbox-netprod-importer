import cachetools
from collections import defaultdict
import json
import re
import logging

from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from netbox_netprod_importer.vendors import _AbstractVendorParser
from .constants import InterfacesRegex


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

    def get_interface_type(self, interface):
        super().get_interface_type(interface)

        fn_order = (
            self._parse_type_from_transceiver,
            self._guess_type_from_if_type
        )

        interface_type = "Other"
        for f in fn_order:
            try:
                return f(interface)
            except TypeCouldNotBeParsedError:
                continue

        return interface_type

    def _parse_type_from_transceiver(self, interface):
        from pynxos.errors import CLIError

        try:
            part_num = self._get_transceiver_by_if()[interface]["partnum"]
        except (json.JSONDecodeError, KeyError, CLIError):
            logger.debug("%s has no transceiver detail", interface)
            raise TypeCouldNotBeParsedError()

        for pattern in InterfacesRegex:
            if re.match(pattern.value[0], part_num):
                return pattern.value[1]

        raise TypeCouldNotBeParsedError()

    def _get_transceiver_by_if(self):
        cmd = "show interface transceiver | json"

        if not self.cache.get("transceivers"):
            transceiver_conf_dump = self.device.cli([cmd])[cmd]
            transceivers = json.loads(
                transceiver_conf_dump
            )["TABLE_interface"]["ROW_interface"]

            self.cache["transceivers"] = {
                i["interface"]: i for i in transceivers
            }

        return self.cache["transceivers"]

    def _guess_type_from_if_type(self, interface):
        from pynxos.errors import CLIError

        try:
            status = self._get_ifstatus_by_if()[interface]
            if_speed, if_type = status["speed"], status["type"]
        except (json.JSONDecodeError, KeyError, CLIError):
            raise TypeCouldNotBeParsedError()

        if not if_type.strip("-"):
            try:
                if int(if_speed) == 1000:
                    return InterfacesRegex.eth1000.value[1]
            except ValueError:
                pass
        else:
            for pattern in InterfacesRegex:
                if re.match(pattern.value[0], if_type):
                    return pattern.value[1]

        raise TypeCouldNotBeParsedError()

    def _get_ifstatus_by_if(self):
        cmd = "show interface status | json"

        if not self.cache.get("ifstatus"):
            status_conf_dump = self.device.cli([cmd])[cmd]
            status = json.loads(
                status_conf_dump
            )["TABLE_interface"]["ROW_interface"]

            self.cache["ifstatus"] = {
                i["interface"]: i for i in status
            }

        return self.cache["ifstatus"]
