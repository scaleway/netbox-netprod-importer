import re

from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from netbox_netprod_importer.vendors.constants import NetboxInterfaceTypes
from .constants import InterfacesRegex
from .base import CiscoParser


class IOSParser(CiscoParser):
    def get_interface_type(self, interface):
        super().get_interface_type(interface)

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
            status_conf_dump = self.device.cli([cmd])[cmd]
            self.cache["ifstatus"] = {}
            for l in status_conf_dump.splitlines()[1:]:
                split_l = l.split()
                if_abrev = split_l[0]
                if_type = split_l[-1]

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
