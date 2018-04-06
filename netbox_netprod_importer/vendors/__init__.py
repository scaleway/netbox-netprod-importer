from enum import Enum
from .cisco import NXOSParser
from .juniper import JunOSParser

__all__ = (
    "NXOSParser", "JunOSParser", "DeviceParsers"
)


class DeviceParsers(Enum):
    junos = JunOSParser
    nxos = NXOSParser
