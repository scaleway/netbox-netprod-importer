import os
import napalm
import pytest

from netbox_netprod_importer.importer import (
    napalm as importer_napalm, DeviceImporter
)


BASE_PATH = os.path.dirname(__file__)


class TestOtherNeighboursParcer():
    parser = None
    profile = None
    path = "mock_driver/specific"
    discovery_protocol = None

    @pytest.fixture(autouse=True)
    def build_importer(self, monkeypatch):
        if not self.profile:
            return
        self._mock_get_network_driver(monkeypatch)
        self.parser = DeviceImporter(
            "localhost", self.profile, "foo",
            napalm_optional_args={
                "path": os.path.join(BASE_PATH, self.path),
                "profile": [self.profile],
            }
        )
        self.parser._get_specific_device_parser(self.profile)
        self.parser.discovery_protocol = self.discovery_protocol

    def _mock_get_network_driver(self, monkeypatch):
        mock_driver = napalm.get_network_driver("mock")
        monkeypatch.setattr(
            importer_napalm,
            "get_network_driver",
            lambda *args: mock_driver
        )

    def test_get_neighbours(self):
        if not self.profile:
            return

        must = [
            {
                "local_port": "Ethernet1/1",
                "hostname": "DEV_1",
                "port": "Ethernet1/1",
            },
            {
                "local_port": "Ethernet1/2",
                "hostname": "DEV_1",
                "port": "Ethernet1/2",
            },
            {
                "local_port": "Ethernet1/3",
                "hostname": "server1",
                "port": "eth0",
            },
            {
                "local_port": "Ethernet1/10",
                "hostname": "server3",
                "port": "enp129s0f0",
            }
        ]
        assert len([x for x in self.parser.get_neighbours()
                    if x not in must]) == 0


class TestNXOS(TestOtherNeighboursParcer):
    profile = "nxos"
    path = "mock_driver/specific/cisco/nxos/"
    discovery_protocol = "cdp"


class TestIOS(TestOtherNeighboursParcer):
    profile = "ios"
    path = "mock_driver/specific/cisco/ios/"
    discovery_protocol = "cdp"
