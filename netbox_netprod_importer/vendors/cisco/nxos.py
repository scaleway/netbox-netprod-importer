import json
import re
import logging

from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from netbox_netprod_importer.vendors.constants import NetboxInterfaceTypes
from .constants import InterfacesRegex
from .base import CiscoParser
from napalm.nxos.nxos import NXOSDriver


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
        cmd = "show interface transceiver" + self._driver_end_selection()

        if not self.cache.get("transceivers"):
            transceiver_conf_dump = self.device.cli([cmd])[cmd]
            transceivers = self._correct_and_convert_to_dict(transceiver_conf_dump)["TABLE_interface"]["ROW_interface"]

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
        cmd = "show interface status" + self._driver_end_selection()

        if not self.cache.get("ifstatus"):
            status_conf_dump = self.device.cli([cmd])[cmd]
            status = self._correct_and_convert_to_dict(status_conf_dump)["TABLE_interface"]["ROW_interface"]

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
                "chassis_id": neighbour id
            }]
        """
        cmd = "show lldp neighbors detail" + self._driver_end_selection()

        cmd_output = self.device.cli([cmd])[cmd]
        neighbours = self._correct_and_convert_to_dict(cmd_output)["TABLE_nbor_detail"]["ROW_nbor_detail"]

        if isinstance(neighbours, dict):
            neighbours = [neighbours]

        for n in neighbours:
            yield {
                "local_port": n["l_port_id"],
                "hostname": n["sys_name"],
                "port": n["port_id"],
                "chassis_id": n["chassis_id"]
            }

    def get_detailed_cdp_neighbours(self):
        """
        Napalm does not support cdp

        :return neighbours: [{
                "local_port": local port name,
                "hostname": neighbour hostname (if handled),
                "port": neighbour port name,
            }]
        """
        cmd = "show cdp neighbors detail" + self._driver_end_selection()

        cmd_output = self.device.cli([cmd])[cmd]
        neighbours = self._correct_and_convert_to_dict(cmd_output)["TABLE_cdp_neighbor_detail_info"][
            "ROW_cdp_neighbor_detail_info"]

        if isinstance(neighbours, dict):
            neighbours = [neighbours]

        for n in neighbours:
            yield {
                "local_port": n["intf_id"],
                "hostname": re.sub("\(.*$", "", n["device_id"], count=1),
                "port": n["port_id"],
            }

    def _driver_end_selection(self) -> str:
        if type(self.device) is NXOSDriver:
            self.device.device.api.cmd_method_raw = "cli"
            return ""
        else:
            return " | json"

    def _correct_and_convert_to_dict(self, cmd_output) -> dict:
        if type(cmd_output) is not dict:
            if not re.search("^{", cmd_output):
                cmd_output = re.sub('^.+\. {', '{', cmd_output, count=1)
            cmd_output = json.loads(cmd_output)
        return cmd_output
