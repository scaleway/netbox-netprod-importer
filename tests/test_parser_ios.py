import os
import napalm
import pytest

from netbox_netprod_importer.vendors.cisco import IOSParser

BASE_PATH = os.path.dirname(__file__)


class TestIOSParser():
    device = None

    @pytest.fixture(autouse=True)
    def build_device(self, monkeypatch):
        driver = napalm.get_network_driver("mock")

        optional_args = {
            "path": os.path.join(BASE_PATH, "mock_driver/specific/cisco/ios"),
            "profile": ["ios"],
        }
        self.device = driver(
            "localhost", "foo", "bar", optional_args=optional_args
        )
        self.device.open()
        self.parser = IOSParser(self.device)


    def test_get_interface_type(self):
        assert '1000BASE-T (1GE)' == self.parser.get_interface_type(
            "GigabitEthernet1/0/24")
        assert 'SFP (1GE)' == self.parser.get_interface_type(
            "GigabitEthernet1/0/28"
        )
        assert 'SFP+ (10GE)' == self.parser.get_interface_type(
            "TenGigabitEthernet1/1/1"
        )
        assert 'SFP+ (10GE)' == self.parser.get_interface_type(
            "TenGigabitEthernet1/1/6"
        )
        assert 'SFP+ (10GE)' == self.parser.get_interface_type(
            "TenGigabitEthernet1/2/6"
        )
        assert 'Other' == self.parser.get_interface_type('Po1')
