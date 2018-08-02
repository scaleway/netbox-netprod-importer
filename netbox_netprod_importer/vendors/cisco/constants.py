from enum import Enum


class InterfacesRegex(Enum):
    cfp = (r"^CFP-.*", "CFP (100GE)")
    cfp2 = (r"^CFP2-.*", "CFP2 (100GE)")
    eth100 = (r".*(?i)100Base(-T|TX)", "100BASE-TX (10/100ME)")
    eth1000 = (r".*(?i)1000BASE(-T|TX)", "1000BASE-T (1GE)")
    sfp = (r"^1000BASE-.X", "SFP (1GE)")
    sfp_plus = (r"^(.?WDM-)?SFP-.?10G.*-.*", "SFP+ (10GE)")
    sfp28 = (r"^SFP-.?25G-.*", "SFP28 (25GE)")
    qsfp_plus = (r"^QSFP-(40|4X10)G.*", "QSFP+ (40GE)")
    qsfp28 = (r"^QSFP-(100G|40/100|4SFP25G)-.*", "QSFP+ (40GE)")
    xenpack = (r"^XENPAK-10GB-.*", "XENPACK (10GE)")
    x2 = (r"^X2-10GB-.*", "X2")
