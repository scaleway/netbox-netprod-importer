from abc import ABC, abstractmethod
import logging


logger = logging.getLogger("netbox_importer")


class _AbstractVendorParser(ABC):

    def __init__(self, napalm_device, *args, **kwargs):
        self.device = napalm_device

    @abstractmethod
    def group_interfaces_by_aggreg(self, interfaces):
        logger.debug("Get interfaces types on host %s", self.device.hostname)

    @abstractmethod
    def get_interface_type(self, interface):
        logger.debug(
            "Get type of interface %s on host %s",
            interface, self.device.hostname
        )
