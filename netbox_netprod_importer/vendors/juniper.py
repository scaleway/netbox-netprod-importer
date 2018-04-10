from collections import defaultdict
import re


class JuniperParser():
    def __init__(self, napalm_device):
        self.device = napalm_device

    def group_interfaces_by_aggreg(self, interfaces):
        pass

    def get_interface_type(self, interface, props):
        return "Other"


class JunOSParser(JuniperParser):
    pass
