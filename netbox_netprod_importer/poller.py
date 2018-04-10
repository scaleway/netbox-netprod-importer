from collections import defaultdict
from importlib import import_module
import socket
import napalm

from netbox_netprod_importer.vendors import DeviceParsers


class DevicePoller():
    def __init__(self, host, napalm_driver_name, creds, napalm_optional_args):
        self.host = host

        driver = napalm.get_network_driver(napalm_driver_name)
        self.device = driver(
            hostname=self.host, username=creds[0], password=creds[1],
            optional_args=napalm_optional_args
        )
        self.device.open()
        self.specific_parser = self._get_specific_device_parser(
            napalm_driver_name
        )

    def _get_specific_device_parser(self, os):
        parser_class = getattr(DeviceParsers, os)

        return parser_class(napalm_device=self.device)

    def poll(self):
        props = {}

        props.update(self.resolve_primary_ip())
        self._handle_interfaces_props(props)

    def resolve_primary_ip(self):
        """
        Resolve primary IPs from hostname

        :return: {"primary_ipv4": ipv4, "primary_ipv6": ipv6}, each key will
                 exist if a reverse exists for this host
        """
        main_ip = {}

        assoc_proto_socket = (
            ("primary_ipv4", socket.AF_INET), ("primary_ipv6", socket.AF_INET6)
        )
        for proto, socket_type in assoc_proto_socket:
            try:
                main_ip[proto] = socket.getaddrinfo(
                    self.host, None, socket_type
                )
            except socket.gaierror:
                continue

        return main_ip

    def _handle_interfaces_props(self, props):
        napalm_interfaces = self.get_interfaces()

        interfaces = {}
        for ifname, napalm_ifprops in napalm_interfaces:
            interfaces[ifname] = {
                "enabled": napalm_ifprops["is_enabled"],
                "description": napalm_ifprops["description"],
                "mac_address": napalm_ifprops["mac-address"],
                "mtu": napalm_ifprops.get(["mtu"]),
                "type": self.specific_parser.get_interface_type(ifname),
            }

        interfaces = self.get_ip_by_interface(interfaces)

        return props

    def get_interfaces(self):
        return self.device.get_interfaces()

    def get_ip_by_interface(self, interfaces=None):
        if interfaces is None:
            interfaces = defaultdict(dict)

        for ifname, props in self.device.get_interfaces_ip().items():
            ip = {
                proto: props[proto] for proto in ("ipv4", "ipv6")
                if props.get(proto, None)
            }

            interfaces[ifname].update(ip)

        return interfaces
