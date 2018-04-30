import os
import napalm
import pytest

from netbox_netprod_importer.vendors.cisco import NXOSParser


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

    @pytest.mark.skip(reason="mocks not yet implemented")
    def test_group_interfaces_by_aggreg_multiple_netif(self):
        interfaces =  sorted((
            "mgmt0", "Ethernet1/1", "Ethernet1/2", "Ethernet1/3",
            "port-channel10", "port-channel11", "port-channel12", "Vlan1",
            "Vlan200",
        ))

        expected_port_channels = {
            "port-channel10": ["Ethernet1/1", "Ethernet1/3"],
            "port-channel12": ["Ethernet1/2"],
        }

        interfaces = sorted(("Ethernet1/1", ))

        port_channels = self.parser.group_interfaces_by_aggreg(interfaces)

        assert port_channels == expected_port_channels
