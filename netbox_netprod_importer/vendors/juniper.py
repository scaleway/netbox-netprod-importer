from collections import defaultdict
import re

from netbox_netprod_importer.vendors import _AbstractVendorParser


class JuniperParser(_AbstractVendorParser):

    def group_interfaces_by_aggreg(self, interfaces):
        super().group_interfaces_by_aggreg(interfaces)
        pass

    def get_interface_type(self, interface):
        super().group_interfaces_by_aggreg(interface)
        return "Other"


class JunOSParser(JuniperParser):
    pass
