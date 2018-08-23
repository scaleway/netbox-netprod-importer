from enum import Enum


class NetboxInterfaceTypes(Enum):
    cfp = "CFP (100GE)"
    cfp2 = "CFP2 (100GE)"
    eth100 = "100BASE-TX (10/100ME)"
    eth1000 = "1000BASE-T (1GE)"
    sfp = "SFP (1GE)"
    sfp_plus = "SFP+ (10GE)"
    sfp28 = "SFP28 (25GE)"
    qsfp_plus = "QSFP+ (40GE)"
    qsfp28 = "QSFP+ (40GE)"
    xenpack = "XENPACK (10GE)"
    x2 = "X2"
    xfp = "XFP (10GE)"
