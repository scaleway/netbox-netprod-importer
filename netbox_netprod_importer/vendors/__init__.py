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
