from abc import ABC, abstractmethod
import logging


logger = logging.getLogger("netbox_importer")


class _AbstractVendorParser(ABC):

    def __init__(self, napalm_device, *args, **kwargs):
        self.device = napalm_device

    @abstractmethod
    def get_interfaces_lag(self, interfaces):
        logger.debug("Get interfaces LAG on host %s", self.device.hostname)
        return {}

    @abstractmethod
    def get_interface_type(self, interface):
        logger.debug(
            "Get type of interface %s on host %s",
            interface, self.device.hostname
        )

    def get_all_derivatives_for_netif(self, interface):
        """
        Get all possible derivatives for an interface name
        """
        yield interface

    def get_detailed_lldp_neighbours(self):
        """
        Napalm does not show id for neighbours. Gives a little more info

        :return neighbours: [{
                "local_port": local port name,
                "hostname": neighbour hostname (if handled),
                "port": neighbour port name,
                "mgmt_id": neighbour id
            }]
        """
        raise NotImplementedError()
