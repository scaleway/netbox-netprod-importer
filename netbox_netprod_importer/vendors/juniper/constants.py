from enum import Enum


class InterfacesRegex(Enum):
    eth100 = r".*100 Base(-T|TX)"
    eth1000 = r".*1000 Base(-T|TX)"
    sfp = r"^SFP-.?G.*"
    sfp_plus = r"^(.?WDM-)?SFP.?-.?10G.*-.*"
    qsfp_plus = r"QSFP\+"
    xfp = r"XFP"
