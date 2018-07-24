from abc import ABC, abstractmethod
import logging


logger = logging.getLogger("netbox_importer")


class _AbstractVendorParser(ABC):

    def __init__(self, napalm_device, *args, **kwargs):
        self.device = napalm_device

    @abstractmethod
    def group_interfaces_by_aggreg(self, interfaces):
        pass

    @abstractmethod
    def get_interface_type(self, interface):
        pass
