import ipaddress
import os
import socket
import napalm
import pytest

from netbox_netprod_importer.poller import napalm as poller_napalm
from netbox_netprod_importer.poller import DevicePoller


BASE_PATH = os.path.dirname(__file__)


class BaseTestPoller():
    poller = None
    profile = None

    @pytest.fixture(autouse=True)
    def build_poller(self, monkeypatch):
        self._mock_get_network_driver(monkeypatch)
        self.poller = DevicePoller(
            "localhost", self.profile, "foo",
            napalm_optional_args={
                "path": os.path.join(BASE_PATH, "mock_driver"),
                "profile": [self.profile],
            }
        )
        self.poller._get_specific_device_parser(self.profile)

    def _mock_get_network_driver(self, monkeypatch):
        mock_driver = napalm.get_network_driver("mock")
        monkeypatch.setattr(
            poller_napalm,
            "get_network_driver",
            lambda *args: mock_driver
        )

    def test_resolve_primary_ip(self):
        ip = self.poller.resolve_primary_ip()

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
        ip = self.poller.resolve_primary_ip()

        assert not ip

    def test_resolve_primary_ip_missing_AAAA(self, mocker):
        mocker.patch(
            "socket.getaddrinfo", side_effect=(mocker.DEFAULT, socket.gaierror)
        )
        ip = self.poller.resolve_primary_ip()

        assert sorted(ip.keys()) == sorted(("primary_ipv4", ))

    def test_get_interfaces_ifnames(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        interfaces = self.poller.get_interfaces()

        if_names =  (
            "mgmt0", "Ethernet1/1", "Ethernet1/2", "port-channel10",
            "port-channel11", "port-channel12", "Vlan1", "Vlan200",
            "Ethernet101/1/1", "Ethernet101/1/2",
        )

        assert sorted(interfaces.keys()) == sorted(if_names)

    def stub_get_interface_type(self, monkeypatch):
        monkeypatch.setattr(
            self.poller.specific_parser,
            "get_interface_type",
            lambda *args: None
        )

    def test_get_interfaces_ifprop(self, monkeypatch):
        self.stub_get_interface_type(monkeypatch)
        interfaces = self.poller.get_interfaces()

        assert interfaces["Ethernet1/2"]["enabled"]
        assert interfaces["Ethernet1/2"]["description"] == "dfe-dc2-2-pub"
        assert interfaces["Ethernet1/2"]["mac_address"] == "CC:46:D6:6E:0F:79"


class TestNXOSPoller(BaseTestPoller):
    profile = "nxos"


class TestJunOSPoller(BaseTestPoller):
    profile = "junos"
