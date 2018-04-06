from enum import Enum


class InterfacesRegex(Enum):
    eth1000 = (r"^1000BASE-T", "1000BASE-T (1GE)")
    sfp = (r"^1000BASE-.X", "SFP (1GE)")
    sfp_plus = (r"^(.?WDM-)?SFP-.?10G.?-.*", "SFP+ (10GE)")
    sfp28 = (r"^SFP-.?25G-.*", "SFP28 (25GE)")
    qsfp_plus = (r"^QSFP-(40|4X10)G.*", "QSFP+ (40GE)")
    xenpack = (r"^XENPAK-10GB-.*", "XENPACK (10GE)")
    x2 = (r"^X2-10GB-.*", "X2")
