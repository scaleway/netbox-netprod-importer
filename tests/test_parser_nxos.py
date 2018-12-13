import os
import napalm
import pytest

from netbox_netprod_importer.vendors.cisco import NXOSParser
from netbox_netprod_importer.vendors.constants import NetboxInterfaceTypes


BASE_PATH = os.path.dirname(__file__)


class TestNXOSParser():
    device = None

    @pytest.fixture(autouse=True)
    def build_device(self, monkeypatch):
        driver = napalm.get_network_driver("mock")

        optional_args = {
            "path": os.path.join(BASE_PATH, "mock_driver/specific/cisco/nxos"),
            "profile": ["nxos"],
        }
        self.device = driver(
            "localhost", "foo", "bar", optional_args=optional_args
        )
        self.device.open()
        self.parser = NXOSParser(self.device)

    def test_get_interfaces_lag(self):
        interfaces = ("Ethernet1/1", )
        expected_port_channels = {
            "Ethernet1/1": "port-channel10"
        }

        port_channels = self.parser.get_interfaces_lag(interfaces)

        assert port_channels == expected_port_channels

    def test_get_interfaces_lag_multiple_netif(self):
        interfaces = [
            "Ethernet1/1", "Ethernet1/2", "Ethernet1/3", "mgmt0",
            "port-channel10", "port-channel11", "port-channel12", "Vlan200",
        ]

        expected_port_channels = {
            "Ethernet1/1": "port-channel10",
            "Ethernet1/2": "port-channel12",
            "Ethernet1/3": "port-channel10",
        }

        port_channels = self.parser.get_interfaces_lag(interfaces)

        assert port_channels == expected_port_channels

    def test_get_interface_type_cfp(self):
        assert (
            self.parser.get_interface_type("Ethernet1/1") ==
            NetboxInterfaceTypes.cfp.value
        )

    def test_get_interface_type_cfp2(self):
        assert (
            self.parser.get_interface_type("Ethernet1/2") ==
            NetboxInterfaceTypes.cfp2.value
        )

    def test_get_interface_type_eth1000(self):
        assert (
            self.parser.get_interface_type("Ethernet1/3") ==
            NetboxInterfaceTypes.eth1000.value
        )

    def test_get_interface_type_sfp(self):
        assert (
            self.parser.get_interface_type("Ethernet1/4") ==
            NetboxInterfaceTypes.sfp.value
        )

    def test_get_interface_type_sfp_plus(self):
        assert (
            self.parser.get_interface_type("Ethernet1/5") ==
            NetboxInterfaceTypes.sfp_plus.value
        )

    def test_get_interface_type_sfp28(self):
        assert (
            self.parser.get_interface_type("Ethernet1/6") ==
            NetboxInterfaceTypes.sfp28.value
        )

    def test_get_interface_type_qsfp_plus(self):
        assert (
            self.parser.get_interface_type("Ethernet1/7") ==
            NetboxInterfaceTypes.qsfp_plus.value
        )

    def test_get_interface_type_qsfp28(self):
        assert (
            self.parser.get_interface_type("Ethernet1/8") ==
            NetboxInterfaceTypes.qsfp28.value
        )

    def test_get_interface_type_xenpack(self):
        assert (
            self.parser.get_interface_type("Ethernet1/9") ==
            NetboxInterfaceTypes.xenpack.value
        )

    def test_get_interface_type_x2(self):
        assert (
            self.parser.get_interface_type("Ethernet1/10") ==
            NetboxInterfaceTypes.x2.value
        )

    def test_get_interface_type_no_transceiver(self):
        assert self.parser.get_interface_type("mgmt0") == "Other"
