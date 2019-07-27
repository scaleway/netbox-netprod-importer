import re
import logging
from collections import defaultdict

from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from netbox_netprod_importer.vendors.constants import NetboxInterfaceTypes
from .constants import InterfacesRegex
from .base import CiscoParser


logger = logging.getLogger("netbox_importer")


class IOSParser(CiscoParser):
    def get_interfaces_lag(self, interfaces):
        super().get_interfaces_lag(interfaces)

        interfaces_lag = defaultdict(list)
        for interface in sorted(interfaces):
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
        if re.search(r"^Vlan(\d*)|^Tunnel(\d+)", interface):
            return "Virtual"

        interface_type = "Other"
        try:
            cisco_if_type = self._guess_type_from_if_type(interface)

            for pattern_iftype in InterfacesRegex:
                pattern = pattern_iftype.value
                if re.match(pattern, cisco_if_type):
                    return getattr(
                        NetboxInterfaceTypes, pattern_iftype.name
                    ).value
        except TypeCouldNotBeParsedError:
            pass

        return interface_type

    def _guess_type_from_if_type(self, interface):
        from pynxos.errors import CLIError

        try:
            abrev_if = self.get_abrev_if(interface)
            return self._get_ifstatus_by_abrev_if()[abrev_if]
        except (KeyError, CLIError):
            raise TypeCouldNotBeParsedError()

    def _get_ifstatus_by_abrev_if(self):
        cmd = "show interface status"

        if not self.cache.get("ifstatus"):
            status_conf_dump = self.device.cli([cmd])[cmd].strip()
            self.cache["ifstatus"] = {}
            start = status_conf_dump.find('Type')
            for l in status_conf_dump.splitlines()[1:]:
                split_l = l.split(maxsplit=1)
                if_abrev = split_l[0]
                try:
                    if_type = l[start:]
                except:
                    if_type = None

                self.cache["ifstatus"][if_abrev] = if_type

        return self.cache["ifstatus"]

    def get_detailed_cdp_neighbours(self):
        cmd = "show cdp neighbors detail"
        cmd_output = self.device.cli([cmd])[cmd]
        cmd_output = re.split('---+\n', cmd_output)
        neighbours = []
        for cdp_port_info in cmd_output:
            if len(cdp_port_info):
                info_port = re.split('\n\n', cdp_port_info)[0].split('\n')
                hostname = local_port = port = ''
                for line in info_port:
                    if line.startswith('Device'):
                        hostname = line.split(':')[1].strip()
                    elif line.startswith('Interface'):
                        local_port, port = line.split(',')
                        local_port = local_port.split(':')[1].strip()
                        port = port.split(':')[1].strip()
                neighbours.append(
                    {
                        "local_port": local_port,
                        "hostname": hostname,
                        "port": port
                    }
                )
        for n in neighbours:
            yield n

    def get_interface_mode(self, interface):
        from pynxos.errors import CLIError
        try:
            return self._get_interfaces_mode()[
                self.get_abrev_if(interface)].get("oper_mode")
        except (KeyError, CLIError):
            logger.debug("Switch %s, show interface switchport cmd error",
                         self.device.hostname)
        return None

    def get_interface_access_vlan(self, interface):
        from pynxos.errors import CLIError
        try:
            return self._get_interfaces_mode()[
                self.get_abrev_if(interface)].get("access_vlan")
        except (KeyError, CLIError):
            logger.debug("Switch %s, show interface switchport cmd error",
                         self.device.hostname)
        return None

    def get_interface_netive_vlan(self, interface):
        from pynxos.errors import CLIError
        try:
            return self._get_interfaces_mode()[
                self.get_abrev_if(interface)].get("native_vlan")
        except (KeyError, CLIError):
            logger.debug("Switch %s, show interface switchport cmd error",
                         self.device.hostname)
        return None

    def _get_interfaces_mode(self):
        cmd = "show interface switchport"

        if not self.cache.get("mode"):
            mode_conf_dump = self.device.cli([cmd])[cmd]
            mode_conf_lines = re.split(r"(^Name: \S+$)", mode_conf_dump, flags=re.M)
            mode_conf_lines.pop(0)
            if len(mode_conf_lines) % 2 != 0:
                raise ValueError("Unexpected output data in '{}':\n\n{}".format(
                    cmd, mode_conf_lines
                ))
            mode_conf_iter = iter(mode_conf_lines)
            try:
                new_mode = [line + next(mode_conf_iter, "") for line in mode_conf_iter]
            except TypeError:
                raise ValueError()

            interfaces_mode = {}
            for entry in new_mode:
                grp = [
                    r"^Name:\s+(?P<interface>\S+)",
                    r"^Administrative Mode:\s+(?P<oper_mode>static access|trunk|access)",
                    r"^Access Mode VLAN:\s+(?P<access_vlan>\d+)",
                    r"^Trunking Native Mode VLAN:\s+(?P<native_valn>\d+)"
                ]
                inf_mode = {}
                for g in grp:
                    find = re.search(g, entry, re.MULTILINE)
                    if find:
                        inf_mode[find.lastgroup] = find.group(find.lastgroup)
                if inf_mode.get("interface"):
                    interfaces_mode[inf_mode["interface"]] = inf_mode

            self.cache["mode"] = interfaces_mode

        return self.cache["mode"]

    def get_vlans(self):
        """
        Napalm does not support vlan
        but there are issues https://github.com/napalm-automation/napalm/issues/927
        PR: https://github.com/napalm-automation/napalm/pull/948

        :return vlans:
            vlan_id, {
                "name": vlan name,
                "interfaces": list interfaces dict
            }
        """
        interfaces = self.device.get_interfaces()
        interface_dict = {}
        for interface, data in interfaces.items():
            interface_dict[self.get_abrev_if(interface)] = interface

        command = "show vlan all-ports"
        output = self.device.cli([command])[command]
        if output.find("Invalid input detected") >= 0:
            yield from self._get_vlan_from_id(interface_dict)
        else:
            yield from self._get_vlan_all_ports(interface_dict, output)

    def _get_vlan_all_ports(self, interface_dict, output):
        find_regexp = r"^(\d+)\s+(\S+)\s+\S+\s+([A-Z][a-z].*)$"
        find = re.findall(find_regexp, output, re.MULTILINE)
        for v in find:
            yield v[0], {
                "name": v[1],
                "interfaces": [
                    interface_dict[x.strip()] for x in v[2].split(",")
                ],
            }
        find_regexp = r"^(\d+)\s+(\S+)\s+\S+$"
        find = re.findall(find_regexp, output, re.MULTILINE)
        for v in find:
            yield v[0], {"name": v[1], "interfaces": []}

    def _get_vlan_from_id(self, interface_dict):
        command = "show vlan brief"
        output = self.device.cli([command])[command]
        vlan_regexp = r"^(\d+)\s+(\S+)\s+\S+.*$"
        find_vlan = re.findall(vlan_regexp, output, re.MULTILINE)
        for vlan in find_vlan:
            command = "show vlan id {}".format(vlan[0])
            output = self.device.cli([command])[command]
            interface_regex = r"{}\s+{}\s+\S+\s+([A-Z][a-z].*)$".format(
                vlan[0], vlan[1]
            )
            interfaces = re.findall(interface_regex, output, re.MULTILINE)
            if len(interfaces) == 1:
                yield vlan[0], {
                    "name": vlan[1],
                    "interfaces": [
                        interface_dict[x.strip()] for x in interfaces[0].split(",")
                    ],
                }
            elif len(interfaces) == 0:
                yield vlan[0], {"name": vlan[1], "interfaces": []}
            else:
                logger.error(
                    "Switch %s Error parsing for vlan id %s, "
                    "found more values than can be.",
                    self.device.hostname, vlan[0]
                )
                yield None, None
