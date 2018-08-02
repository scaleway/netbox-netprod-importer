import re

from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from .constants import InterfacesRegex
from .base import CiscoParser


class IOSParser(CiscoParser):
    def get_interface_type(self, interface):
        super().get_interface_type(interface)

        interface_type = "Other"
        try:
            cisco_if_type = self._guess_type_from_if_type(interface)
            for pattern in InterfacesRegex:
                if re.match(pattern.value[0], cisco_if_type):
                    return pattern.value[1]
        except TypeCouldNotBeParsedError:
            pass

        return interface_type

    def _guess_type_from_if_type(self, interface):
        from pynxos.errors import CLIError

        try:
            abrev_if = self._get_abrev_if(interface)
            return self._get_ifstatus_by_abrev_if()[abrev_if]
        except (KeyError, CLIError):
            raise TypeCouldNotBeParsedError()

    def _get_ifstatus_by_abrev_if(self):
        cmd = "show interface status | section 1"

        if not self.cache.get("ifstatus"):
            status_conf_dump = self.device.cli([cmd])[cmd]
            self.cache["ifstatus"] = {}
            for l in status_conf_dump.splitlines():
                split_l = l.split()
                if_abrev = split_l[0]
                if_type = split_l[-1]

                self.cache["ifstatus"][if_abrev] = if_type

        return self.cache["ifstatus"]

    def _get_abrev_if(self, interface):
        if_index_re = re.search(r"\d.*", interface)
        if_index_re = if_index_re.group() if if_index_re else ""

        return interface[:2] + if_index_re
