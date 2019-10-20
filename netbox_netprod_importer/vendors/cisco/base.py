import cachetools
import re

from netbox_netprod_importer.vendors import _AbstractVendorParser


class CiscoParser(_AbstractVendorParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cache = cachetools.TTLCache(128, 600)

    @staticmethod
    def get_abrev_if(interface):
        if_index_re = re.search(r"\d.*", interface)
        if_index_re = if_index_re.group() if if_index_re else ""

        if interface.lower().startswith("eth"):
            prefix = interface[:3]
        else:
            prefix = interface[:2]

        return prefix + if_index_re

    def get_interface_vlans(self, interface):

        if not self.cache.get("vlan"):
            self.cache["ttl"] = 600
            self.cache["vlan"] = {}
            for vlan, data in self.get_vlans():
                for iface in data["interfaces"]:
                    if not self.cache["vlan"].get(iface):
                        self.cache["vlan"][iface] = []
                    self.cache["vlan"][iface].append(vlan)
        return self.cache["vlan"].get(interface)


