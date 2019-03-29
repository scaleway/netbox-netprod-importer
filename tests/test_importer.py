import ipaddress
import os
import socket
import napalm
import pytest
import json

from netbox_netprod_importer.importer import (
    napalm as importer_napalm, DeviceImporter
)
from netbox_netprod_importer.exceptions import NoReverseFoundError


BASE_PATH = os.path.dirname(__file__)


class BaseTestImporter():
    importer = None
    profile = None
    path = "mock_driver/global"

    @pytest.fixture(autouse=True)
    def build_importer(self, monkeypatch):
        self._mock_get_network_driver(monkeypatch)
        self.importer = DeviceImporter(
            "localhost", self.profile, "foo",
            napalm_optional_args={
                "path": os.path.join(BASE_PATH, self.path),
                "profile": [self.profile],
            }
        )
        self.importer._get_specific_device_parser(self.profile)

    def _mock_get_network_driver(self, monkeypatch):
        mock_driver = napalm.get_network_driver("mock")
        monkeypatch.setattr(
            importer_napalm,
            "get_network_driver",
            lambda *args: mock_driver
        )

    def test_resolve_primary_ip(self, mocker):
        m = mocker.patch("socket.getaddrinfo")
        m.side_effect = [[[None]*4 + [["127.0.0.1"]]], [[None]*4 + [["::1"]]]]
        with self.importer:
            ip = self.importer.resolve_primary_ip()

        assert (
            ipaddress.ip_address(ip["primary_ip4"]) ==
            ipaddress.ip_address("127.0.0.1")
        )
        assert (
            ipaddress.ip_address(ip["primary_ip6"]) ==
            ipaddress.ip_address("::1")
        )

    def test_resolve_primary_ip_error(self, mocker):
        mocker.patch("socket.getaddrinfo", side_effect=socket.gaierror)

        with pytest.raises(NoReverseFoundError):
            with self.importer:
                self.importer.resolve_primary_ip()

    def test_resolve_primary_ip_missing_AAAA(self, mocker):
        mocker.patch(
            "socket.getaddrinfo", side_effect=(mocker.DEFAULT, socket.gaierror)
        )
        with self.importer:
            ip = self.importer.resolve_primary_ip()

        assert sorted(ip.keys()) == sorted(("primary_ip4", ))

    def stub_get_interface_type(self, monkeypatch):
        monkeypatch.setattr(
            self.importer.specific_parser,
            "get_interface_type",
            lambda *args: None
        )


class TestIOSImporter(BaseTestImporter):
    profile = "ios"
    path = "mock_driver/global/cisco/ios/"

    def test_get_interfaces(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        with self.importer:
            interfaces = self.importer.get_interfaces()
        with open(
                "{}/{}/test_get_interfaces.json".format(BASE_PATH, self.path),
                "r"
        ) as myfile:
            data = myfile.read()

        assert interfaces == json.loads(data)

class TestNXOSImporter(BaseTestImporter):
    profile = "nxos"
    path = "mock_driver/global/cisco/nxos/"

    def test_get_interfaces_ifnames(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        with self.importer:
            interfaces = self.importer.get_interfaces()

            if_names = (
                'Ethernet1/1', 'Ethernet1/10', 'Ethernet1/11', 'Ethernet1/12',
                'Ethernet1/13', 'Ethernet1/14', 'Ethernet1/15', 'Ethernet1/16',
                'Ethernet1/17', 'Ethernet1/18', 'Ethernet1/19', 'Ethernet1/2',
                'Ethernet1/20', 'Ethernet1/21', 'Ethernet1/22', 'Ethernet1/23',
                'Ethernet1/24', 'Ethernet1/25', 'Ethernet1/26', 'Ethernet1/27',
                'Ethernet1/28', 'Ethernet1/29', 'Ethernet1/3', 'Ethernet1/30',
                'Ethernet1/31', 'Ethernet1/32', 'Ethernet1/33', 'Ethernet1/34',
                'Ethernet1/35', 'Ethernet1/36', 'Ethernet1/37', 'Ethernet1/38',
                'Ethernet1/39', 'Ethernet1/4', 'Ethernet1/40', 'Ethernet1/41',
                'Ethernet1/42', 'Ethernet1/43', 'Ethernet1/44', 'Ethernet1/45',
                'Ethernet1/46', 'Ethernet1/47', 'Ethernet1/48', 'Ethernet1/49',
                'Ethernet1/5', 'Ethernet1/50', 'Ethernet1/51', 'Ethernet1/52',
                'Ethernet1/53', 'Ethernet1/54', 'Ethernet1/6', 'Ethernet1/7',
                'Ethernet1/8', 'Ethernet1/9', 'Vlan1', 'Vlan177', 'mgmt0',
                'port-channel100', 'port-channel101', 'port-channel12',
                'port-channel22', 'port-channel23', 'port-channel24',
                'port-channel25', 'port-channel26', 'port-channel27',
                'port-channel28', 'port-channel29', 'port-channel30',
                'port-channel31', 'port-channel32', 'port-channel33',
                'port-channel34', 'port-channel35', 'port-channel36',
                'port-channel37', 'port-channel38', 'port-channel39',
                'port-channel40', 'port-channel41', 'port-channel42',
                'port-channel43', 'port-channel44', 'port-channel45',
                'port-channel46',
            )

            assert sorted(interfaces.keys()) == sorted(if_names)

    def test_get_interfaces_ifprop(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        with self.importer:
            interfaces = self.importer.get_interfaces()

        assert interfaces["Ethernet1/2"]["enabled"]
        assert interfaces["Ethernet1/2"]["description"] == "is simply"
        assert (
            interfaces["Ethernet1/2"]["mac_address"].upper() ==
            "00:00:00:00:00:69"
        )

    def test_fill_interfaces_ip_no_dict(self):
        with self.importer:
            ip_by_interfaces = self.importer.fill_interfaces_ip()

        expected_ip = tuple(
            ipaddress.ip_interface(ip)
            for ip in sorted(("203.0.113.1/24", "2001:db8:407::1/48"))
        )

        output_ip = tuple(
            ipaddress.ip_interface(ip)
            for ip in sorted(ip_by_interfaces["Vlan1"]["ip"])
        )

        assert output_ip == expected_ip

    def test_fill_interfaces_ip_ifnames(self):
        with self.importer:
            ip_by_interfaces = self.importer.fill_interfaces_ip()

        expected_if = ("mgmt0", "Vlan1", "Vlan177")
        assert sorted(expected_if) == sorted(ip_by_interfaces.keys())

    def test_fill_interfaces_with_dict(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        with self.importer:
            interfaces = self.importer.get_interfaces()
            self.importer.fill_interfaces_ip(interfaces)

        for ifname in ("mgmt0", "Vlan1", "Vlan177"):
            assert interfaces[ifname]["ip"]

class TestJunOSImporter(BaseTestImporter):
    profile = "junos"
    path = "mock_driver/global/junos/"

    def test_get_interfaces_ifnames(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        with self.importer:
            interfaces = self.importer.get_interfaces()

            if_names = (
                "lo0", "ge-0/0/0", "ge-0/0/1", "ae10", "ae11", "ae12",
                "ge-1/0/0", "ge-1/0/1", "vlan.1", "vlan.200"
            )

            assert sorted(interfaces.keys()) == sorted(if_names)

    def test_get_interfaces_ifprop(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        with self.importer:
            interfaces = self.importer.get_interfaces()

        assert interfaces["ge-0/0/1"]["enabled"]
        assert interfaces["ge-0/0/1"]["description"] == "dummy text"
        assert (
            interfaces["ge-0/0/1"]["mac_address"].upper() ==
            "CC:46:D6:6E:0F:79"
        )
