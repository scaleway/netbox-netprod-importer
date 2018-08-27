import json
import re
import logging

from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from netbox_netprod_importer.vendors.constants import NetboxInterfaceTypes
from .constants import InterfacesRegex
from .base import CiscoParser


logger = logging.getLogger("netbox_importer")


class NXOSParser(CiscoParser):
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

        for pattern_iftype in InterfacesRegex:
            pattern = pattern_iftype.value
            if re.match(pattern, part_num):
                return getattr(NetboxInterfaceTypes, pattern_iftype.name).value

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
                    return NetboxInterfaceTypes.eth1000.value
            except ValueError:
                pass
        else:
            for pattern in InterfacesRegex:
                if re.match(pattern.value, if_type):
                    return getattr(NetboxInterfaceTypes, pattern.name).value

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

    def get_detailed_lldp_neighbours(self):
        """
        Napalm does not show id for neighbours. Gives a little more info

        :return neighbours: [{
                "local_port": local port name,
                "hostname": neighbour hostname (if handled),
                "port": neighbour port name,
                "mgmt_id": neighbour id
            }]
        """
        cmd = "show lldp neighbors detail | json"

        cmd_output = self.device.cli([cmd])[cmd]
        neighbours = json.loads(
            cmd_output
        )["TABLE_nbor_detail"]["ROW_nbor_detail"]

        for n in neighbours:
            yield {
                "local_port": n["l_port_id"],
                "hostname": n["sys_name"],
                "port": n["port_id"],
                "chassis_id": n["chassis_id"]
            }
