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
