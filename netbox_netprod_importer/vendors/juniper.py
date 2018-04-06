from collections import defaultdict
import re


class JuniperParser():
    def __init__(self, napalm_device):
        self.device = napalm_device

    def group_interfaces_by_aggreg(self, interfaces):
        pass

    @staticmethod
    def fill_interface_type(interfaces):
        pass


class JunOSParser(JuniperParser):
    pass
