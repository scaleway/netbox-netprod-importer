from simplejson.errors import JSONDecodeError

class NoReverseFoundError(Exception):
    def __init__(self, host):
        super().__init__("No reverse found for host {}".format(host))


class TypeCouldNotBeParsedError(Exception):
    pass


class DeviceNotFoundError(Exception):
    def __init__(self, hostname):
        super().__init__("Device {} not found on Netbox".format(hostname))
        self.hostname = hostname


class _NetboxPushingError(Exception):
    netbox_exc = None

    def _extract_netbox_error(self):
        try:
            return self.netbox_exc.response.json()
        except JSONDecodeError:
            return self.netbox_exc.response.content.decode()


class IPPushingError(_NetboxPushingError):
    def __init__(self, ip, netbox_req_exc):
        self.ip = ip
        self.netbox_exc = netbox_req_exc

        reason = self._extract_netbox_error()
        super().__init__("IP {} could not be created: {} -- {}".format(
            ip, netbox_req_exc, reason
        ))


class NetIfPushingError(_NetboxPushingError):
    def __init__(self, netif_name, netbox_req_exc):
        self.netif_name = netif_name
        self.netbox_exc = netbox_req_exc

        reason = self._extract_netbox_error()
        super().__init__("Interface {} could not be created: {} -- {}".format(
            netif_name, netbox_req_exc, reason
        ))


class NetInterfaceNotFoundError(Exception):
    def __init__(self, netif):
        super().__init__(
            "Network interface {} not found on Netbox".format(netif)
        )
        self.netif = netif


class DeviceNotSupportedError(Exception):
    def __init__(self, hostname):
        super().__init__("Device {} not supported".format(hostname))
        self.hostname = hostname
