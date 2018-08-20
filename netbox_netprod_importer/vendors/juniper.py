from collections import defaultdict
import re

from netbox_netprod_importer.vendors import _AbstractVendorParser


class JuniperParser(_AbstractVendorParser):

    def get_interfaces_lag(self, interfaces):
        return super().get_interfaces_lag(interfaces)

    def get_interface_type(self, interface):
        super().get_interface_type(interface)
        return "Other"

    @staticmethod
    def get_real_ifname(interface):
        ifsplit = interface.split(".")
        if len(ifsplit) > 1 and ifsplit[0].lower() != "vlan":
            return ifsplit[0]
        else:
            return interface


class JunOSParser(JuniperParser):
    pass
