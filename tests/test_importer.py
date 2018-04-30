import ipaddress
import os
import socket
import napalm
import pytest

from netbox_netprod_importer.importer import napalm as importer_napalm
from netbox_netprod_importer.importer import DeviceImporter


BASE_PATH = os.path.dirname(__file__)


class BaseTestImporter():
    importer = None
    profile = None

    @pytest.fixture(autouse=True)
    def build_importer(self, monkeypatch):
        self._mock_get_network_driver(monkeypatch)
        self.importer = DeviceImporter(
            "localhost", self.profile, "foo",
            napalm_optional_args={
                "path": os.path.join(BASE_PATH, "mock_driver/global"),
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

    def test_resolve_primary_ip(self):
        ip = self.importer.resolve_primary_ip()

        assert (
            ipaddress.ip_address(ip["primary_ipv4"]) ==
            ipaddress.ip_address("127.0.0.1")
        )
        assert (
            ipaddress.ip_address(ip["primary_ipv6"]) ==
            ipaddress.ip_address("::1")
        )

    def test_resolve_primary_ip_error(self, mocker):
        mocker.patch("socket.getaddrinfo", side_effect=socket.gaierror)
        ip = self.importer.resolve_primary_ip()

        assert not ip

    def test_resolve_primary_ip_missing_AAAA(self, mocker):
        mocker.patch(
            "socket.getaddrinfo", side_effect=(mocker.DEFAULT, socket.gaierror)
        )
        ip = self.importer.resolve_primary_ip()

        assert sorted(ip.keys()) == sorted(("primary_ipv4", ))

    def test_get_interfaces_ifnames(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        interfaces = self.importer.get_interfaces()

        if_names =  (
            "mgmt0", "Ethernet1/1", "Ethernet1/2", "port-channel10",
            "port-channel11", "port-channel12", "Vlan1", "Vlan200",
            "Ethernet101/1/1", "Ethernet101/1/2",
        )

        assert sorted(interfaces.keys()) == sorted(if_names)

    def stub_get_interface_type(self, monkeypatch):
        monkeypatch.setattr(
            self.importer.specific_parser,
            "get_interface_type",
            lambda *args: None
        )

    def test_get_interfaces_ifprop(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        interfaces = self.importer.get_interfaces()

        assert interfaces["Ethernet1/2"]["enabled"]
        assert interfaces["Ethernet1/2"]["description"] == "dfe-dc2-2-pub"
        assert interfaces["Ethernet1/2"]["mac_address"] == "CC:46:D6:6E:0F:79"

    def test_fill_interfaces_ip_no_dict(self):
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
        ip_by_interfaces = self.importer.fill_interfaces_ip()

        expected_if = ("mgmt0", "Vlan1", "Vlan200")
        assert sorted(expected_if) == sorted(ip_by_interfaces.keys())

    def test_fill_interfaces_with_dict(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        interfaces = self.importer.get_interfaces()
        self.importer.fill_interfaces_ip(interfaces)

        for ifname in ("mgmt0", "Vlan1", "Vlan200"):
            assert interfaces[ifname]["ip"]


class TestNXOSImporter(BaseTestImporter):
    profile = "nxos"


class TestJunOSImporter(BaseTestImporter):
    profile = "junos"
