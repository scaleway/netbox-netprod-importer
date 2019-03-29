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

    def test_get_abrev_if(self):
        assert self.parser.get_abrev_if("Ethernet1/1") == "Eth1/1"
        assert self.parser.get_abrev_if("port-channel10") == "po10"

    def test_get_interfaces_lag(self):
        expected_port_channels = {
            "Ethernet1/21": "port-channel12",
            "Ethernet1/22": "port-channel12",
            "Ethernet1/23": "port-channel12",
            "Ethernet1/24": "port-channel12",
            "Ethernet1/37": "port-channel22",
            "Ethernet1/38": "port-channel23",
            "Ethernet1/7": "port-channel24",
            "Ethernet1/8": "port-channel25",
            "Ethernet1/25": "port-channel26",
            "Ethernet1/26": "port-channel27",
            "Ethernet1/27": "port-channel28",
            "Ethernet1/30": "port-channel29",
            "Ethernet1/34": "port-channel30",
            "Ethernet1/1": "port-channel31",
            "Ethernet1/2": "port-channel32",
            "Ethernet1/3": "port-channel33",
            "Ethernet1/31": "port-channel34",
            "Ethernet1/33": "port-channel35",
            "Ethernet1/35": "port-channel36",
            "Ethernet1/36": "port-channel37",
            "Ethernet1/4": "port-channel38",
            "Ethernet1/5": "port-channel39",
            "Ethernet1/6": "port-channel40",
            "Ethernet1/28": "port-channel41",
            "Ethernet1/29": "port-channel42",
            "Ethernet1/12": "port-channel43",
            "Ethernet1/9": "port-channel44",
            "Ethernet1/10": "port-channel45",
            "Ethernet1/11": "port-channel46",
            "Ethernet1/47": "port-channel100",
            "Ethernet1/48": "port-channel100",
            "Ethernet1/43": "port-channel101",
            "Ethernet1/44": "port-channel101"
        }
        port_channels = self.parser.get_interfaces_lag(["Ethernet1/1"])
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

    def test_get_detailed_lldp_neighbours(self):
        must = [
            {
                "local_port": "Eth1/1",
                "hostname": "DEV_1",
                "port": "Eth1/1",
                "chassis_id": "002a.6ad3.380c",
            },
            {
                "local_port": "Eth1/2",
                "hostname": "DEV_1",
                "port": "Eth1/2",
                "chassis_id": "002a.6ad3.380d",
            },
            {
                "local_port": "Eth1/3",
                "hostname": "server1",
                "port": "eth0",
                "chassis_id": "f898.ef9d.2197",
            },
            {
                "local_port": "Eth1/10",
                "hostname": "server3",
                "port": "enp129s0f0",
                "chassis_id": "f898.ef9d.4198",
            }
        ]
        assert len([x for x in self.parser.get_detailed_lldp_neighbours()
                    if x not in must]) == 0
