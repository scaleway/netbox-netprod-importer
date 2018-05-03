import os
import napalm
import pytest

from netbox_netprod_importer.vendors.cisco import NXOSParser
from netbox_netprod_importer.vendors.cisco.constants import InterfacesRegex


BASE_PATH = os.path.dirname(__file__)


class TestNXOSParser():
    @pytest.fixture(autouse=True)
    def build_device(self, monkeypatch):
        driver = napalm.get_network_driver("mock")

        optional_args={
            "path": os.path.join(BASE_PATH, "mock_driver/cisco/nxos"),
            "profile": ["nxos"],
        }
        self.device = driver(
            "localhost", "foo", "bar", optional_args=optional_args
        )
        self.device.open()
        self.parser = NXOSParser(self.device)

    def test_group_interfaces_by_aggreg(self):
        interfaces =  ("Ethernet1/1", )
        expected_port_channels = {
            "port-channel10": ["Ethernet1/1"],
        }

        port_channels = self.parser.group_interfaces_by_aggreg(interfaces)

        assert port_channels == expected_port_channels

    def test_group_interfaces_by_aggreg_multiple_netif(self):
        interfaces =  [
            "Ethernet1/1", "Ethernet1/2", "Ethernet1/3", "mgmt0",
            "port-channel10", "port-channel11", "port-channel12", "Vlan200",
        ]

        expected_port_channels = {
            "port-channel10": ["Ethernet1/1", "Ethernet1/3"],
            "port-channel12": ["Ethernet1/2"],
        }

        port_channels = self.parser.group_interfaces_by_aggreg(interfaces)

        assert port_channels == expected_port_channels

    def test_get_interface_type_cfp(self):
        assert (
            self.parser.get_interface_type("Ethernet1/1") ==
            InterfacesRegex.cfp.value[1]
        )

    def test_get_interface_type_cfp2(self):
        assert (
            self.parser.get_interface_type("Ethernet1/2") ==
            InterfacesRegex.cfp2.value[1]
        )

    def test_get_interface_type_eth1000(self):
        assert (
            self.parser.get_interface_type("Ethernet1/3") ==
            InterfacesRegex.eth1000.value[1]
        )

    def test_get_interface_type_sfp(self):
        assert (
            self.parser.get_interface_type("Ethernet1/4") ==
            InterfacesRegex.sfp.value[1]
        )

    def test_get_interface_type_sfp_plus(self):
        assert (
            self.parser.get_interface_type("Ethernet1/5") ==
            InterfacesRegex.sfp_plus.value[1]
        )

    def test_get_interface_type_sfp28(self):
        assert (
            self.parser.get_interface_type("Ethernet1/6") ==
            InterfacesRegex.sfp28.value[1]
        )

    def test_get_interface_type_qsfp_plus(self):
        assert (
            self.parser.get_interface_type("Ethernet1/7") ==
            InterfacesRegex.qsfp_plus.value[1]
        )

    def test_get_interface_type_qsfp28(self):
        assert (
            self.parser.get_interface_type("Ethernet1/8") ==
            InterfacesRegex.qsfp28.value[1]
        )

    def test_get_interface_type_xenpack(self):
        assert (
            self.parser.get_interface_type("Ethernet1/9") ==
            InterfacesRegex.xenpack.value[1]
        )

    def test_get_interface_type_x2(self):
        assert (
            self.parser.get_interface_type("Ethernet1/10") ==
            InterfacesRegex.x2.value[1]
        )

    def test_get_interface_type_no_transceiver(self):
        assert self.parser.get_interface_type("mgmt0") == "Other"
