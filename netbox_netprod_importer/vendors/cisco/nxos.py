import json
import re
import logging

from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from netbox_netprod_importer.vendors.constants import NetboxInterfaceTypes
from .constants import InterfacesRegex
from .base import CiscoParser
from napalm.nxos.nxos import NXOSDriver
from collections import defaultdict

logger = logging.getLogger("netbox_importer")


class NXOSParser(CiscoParser):
    def get_interface_type(self, interface):
        super().get_interface_type(interface)
        if re.search(r"^Vlan(\d*)|^Tunnel(\d+)", interface):
            return "Virtual"

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
            transceivers = self._correct_and_convert_to_dict(
                transceiver_conf_dump)["TABLE_interface"]["ROW_interface"]

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
            status = self._correct_and_convert_to_dict(status_conf_dump)[
                "TABLE_interface"]["ROW_interface"]

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
        neighbours = self._correct_and_convert_to_dict(cmd_output)[
            "TABLE_nbor_detail"]["ROW_nbor_detail"]

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
        neighbours = self._correct_and_convert_to_dict(cmd_output)[
            "TABLE_cdp_neighbor_detail_info"]["ROW_cdp_neighbor_detail_info"]

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

    def get_interfaces_lag(self, interfaces):
        cmd = "show port-channel summary" + self._driver_end_selection()
        interfaces_lag = defaultdict(list)

        cmd_output = self.device.cli([cmd])[cmd]
        port_cannels = self._correct_and_convert_to_dict(cmd_output)[
            "TABLE_channel"]["ROW_channel"]

        if isinstance(port_cannels, dict):
            port_cannels = [port_cannels]

        for p in port_cannels:
            if not p.get("TABLE_member"):
                continue
            if not p["TABLE_member"].get("ROW_member"):
                continue
            if isinstance(p["TABLE_member"]["ROW_member"], dict):
                member = [p["TABLE_member"]["ROW_member"]]
            else:
                member = p["TABLE_member"]["ROW_member"]
            for interface in member:
                interfaces_lag[interface["port"]] = p["port-channel"]

        return interfaces_lag

    def get_interface_mode(self, interface):
        from pynxos.errors import CLIError
        try:
            return self._get_interfaces_mode()[interface].get("oper_mode")
        except (KeyError, CLIError):
            logger.debug("Switch %s, show interface switchport cmd error",
                         self.device.hostname)
        return None

    def get_interface_access_vlan(self, interface):
        from pynxos.errors import CLIError
        try:
            return int(
                self._get_interfaces_mode()[interface].get("access_vlan")
            )
        except (KeyError, CLIError):
            logger.debug("Switch %s, show interface switchport cmd error",
                         self.device.hostname)
        return None

    def get_interface_netive_vlan(self, interface):
        from pynxos.errors import CLIError
        try:
            return int(
                self._get_interfaces_mode()[interface].get("native_vlan")
            )
        except (KeyError, CLIError):
            logger.debug("Switch %s, show interface switchport cmd error",
                         self.device.hostname)
        return None

    def _get_interfaces_mode(self):
        cmd = "show interface switchport" + self._driver_end_selection()

        if not self.cache.get("mode"):
            mode_conf_dump = self.device.cli([cmd])[cmd]
            mode = self._correct_and_convert_to_dict(mode_conf_dump)[
                "TABLE_interface"]["ROW_interface"]

            self.cache["mode"] = {
                i["interface"]: i for i in mode
            }

        return self.cache["mode"]

    def get_vlans(self):
        """
        Napalm does not support vlan
        but there are issues https://github.com/napalm-automation/napalm/issues/927

        :return vlans:
            vlan_id, {
                "name": vlan name,
                "interfaces": list interfaces dict
            }
        """
        cmd = "show vlan brief" + self._driver_end_selection()

        cmd_output = self.device.cli([cmd])[cmd]
        vlans = self._correct_and_convert_to_dict(cmd_output)[
            "TABLE_vlanbriefxbrief"]["ROW_vlanbriefxbrief"]

        if isinstance(vlans, dict):
            vlans = [vlans]

        for v in vlans:
            yield v["vlanshowbr-vlanid"], {
                "name": v["vlanshowbr-vlanname"],
                "interfaces": self._parse_ports(v["vlanshowplist-ifidx"])
            }

    def _parse_ports(self, vlan_s) -> list:
        vlans = []
        find_regexp = r"^([A-Za-z\/-]+|.*\/)(\d+)-(\d+)$"
        vlan_str = ""

        if isinstance(vlan_s, list):
            for v in vlan_s:
                vlan_str += "," + v
        else:
            vlan_str = vlan_s

        for vls in vlan_str.split(","):
            find = re.findall(find_regexp, vls.strip())
            if find:
                for i in range(int(find[0][1]), int(find[0][2]) + 1):
                    vlans.append(find[0][0] + str(i))
            else:
                vlans.append(vls.strip())
        return vlans
