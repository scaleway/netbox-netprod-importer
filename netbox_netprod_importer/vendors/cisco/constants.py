from enum import Enum


class InterfacesRegex(Enum):
    cfp = r"^CFP-.*"
    cfp2 = r"^CFP2-.*"
    eth100 = r".*(i?)100Base(-T|TX)"
    eth1000 = r".*(i?)1000(BASE|Base)?(-T|TX|X|T)"
    sfp = r"^1000B(ASE|ase)(-.|.)X"
    sfp_plus = r"(^(.?WDM-)?SFP-.?10G.*-.*|^10Gbase-(.R|.?CU.*M))"
    sfp28 = r"^SFP-.?25G-.*"
    qsfp_plus = r"^QSFP-(40|4X10)G.*"
    qsfp28 = r"^QSFP-(100G|40/100|4SFP25G)-.*"
    xenpack = r"^XENPAK-10GB-.*"
    x2 = r"^X2-10GB-.*"
