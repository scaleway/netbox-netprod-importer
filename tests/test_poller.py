import ipaddress
import os
import socket
import napalm
import pytest

from netbox_netprod_importer.poller import DevicePoller


BASE_PATH = os.path.dirname(__file__)


class BaseTestPoller():
    poller = None
    profile = None

    @pytest.fixture(autouse=True)
    def build_poller(self, mocker):
        self._mock_get_network_driver(mocker)
        self.poller = DevicePoller(
            "localhost", self.profile, "foo",
            napalm_optional_args={
                "path": os.path.join(BASE_PATH, "test_mock_driver"),
                "profile": [self.profile],
            }
        )
        self.poller._get_specific_device_parser(self.profile)

    def _mock_get_network_driver(self, mocker):
        mock_config = {
            'method.return_value': napalm.get_network_driver("mock")
        }
        mocker.patch(
            "napalm.get_network_driver", **mock_config
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


class TestNXOSPoller(BaseTestPoller):
    profile = "nxos"


class TestJunOSPoller(BaseTestPoller):
    profile = "junos"
