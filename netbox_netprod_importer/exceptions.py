class NoReverseFoundError(Exception):
    def __init__(self, host):
        super().__init__("No reverse found for host {}".format(host))


class TypeCouldNotBeParsedError(Exception):
    pass


class DeviceNotFoundError(Exception):
    def __init__(self, hostname):
        super().__init__("Device {} not found on Netbox".format(hostname))
        self.hostname = hostname


class DeviceNotSupportedError(Exception):
    def __init__(self, hostname):
        super().__init__("Device {} not supported".format(hostname))
        self.hostname = hostname
