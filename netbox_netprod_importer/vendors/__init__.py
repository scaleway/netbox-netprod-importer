from enum import Enum
from .base import _AbstractVendorParser
from .cisco import NXOSParser, IOSParser
from .juniper import JunOSParser

__all__ = (
    "NXOSParser", "JunOSParser", "DeviceParsers"
)


class DeviceParsers(Enum):
    junos = JunOSParser
    nxos = NXOSParser
    nxos_ssh = NXOSParser
    ios = IOSParser


class StubParser(_AbstractVendorParser):

    def get_interfaces_lag(self, *args, **kwargs):
        return super().get_interfaces_lag(*args, **kwargs)

    def get_interface_type(self, *args, **kwargs):
        return "Other"
