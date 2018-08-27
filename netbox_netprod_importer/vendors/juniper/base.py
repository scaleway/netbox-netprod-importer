from collections import defaultdict
import logging
import defusedxml.lxml
import lxml.etree
# should be a napalm dependency
from jnpr.junos.exception import RpcError
import re

from netbox_netprod_importer.vendors import _AbstractVendorParser
from netbox_netprod_importer.vendors.constants import NetboxInterfaceTypes
from netbox_netprod_importer.exceptions import TypeCouldNotBeParsedError
from .constants import InterfacesRegex


logger = logging.getLogger("netbox_importer")


class JuniperParser(_AbstractVendorParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}

    def get_interfaces_lag(self, interfaces):
        return super().get_interfaces_lag(interfaces)

    def get_interface_type(self, interface):
        return super().get_interface_type(interface)

    @staticmethod
    def get_real_ifname(interface):
        ifsplit = interface.split(".")
        if len(ifsplit) > 1 and ifsplit[0].lower() != "vlan":
            return ifsplit[0]
        else:
            return interface


class JunOSParser(JuniperParser):

    def get_interfaces_lag(self, interfaces):
        interfaces_lag = defaultdict(set)

        try:
            interfaces_info_xml = self.device._rpc(
                self._gen_rpc_request_interfaces_info()
            )
        except RpcError as e:
            logger.debug("RPC error: %s", e)
            raise

        parsed_xml = defusedxml.lxml.fromstring(interfaces_info_xml)

        for ifblock in parsed_xml.xpath(".//physical-interface"):
            ifname = ifblock.xpath("name")[0].text.strip()
            if ifname not in interfaces:
                continue

            bundle_xpath = ifblock.xpath(".//ae-bundle-name")
            if bundle_xpath:
                bundle_name = bundle_xpath[0].text.split(".")[0].strip()
                interfaces_lag[ifname] = bundle_name

        return interfaces_lag

    def _gen_rpc_request_interfaces_info(self):
        get_pic_details_el = lxml.etree.Element("get-interface-information")
        xml_tree = get_pic_details_el.getroottree()

        return lxml.etree.tostring(xml_tree).decode()

    def get_interface_type(self, interface):
        try:
            junos_type = self._guess_type_from_chassis_pic(interface)
        except TypeCouldNotBeParsedError:
            return "Other"

        for pattern_iftype in InterfacesRegex:
            pattern = pattern_iftype.value
            if re.match(pattern, junos_type):
                return getattr(NetboxInterfaceTypes, pattern_iftype.name).value

        return "Other"

    def _guess_type_from_chassis_pic(self, interface):
        pattern = r".*-(\d+)/(\d+)/(\d+)"
        matching_ifname_split = re.match(pattern, interface)

        if not matching_ifname_split:
            logger.debug("Unexpected interface name convention: %s", interface)
            raise TypeCouldNotBeParsedError(interface)

        fpc, pic, port_index = map(int, matching_ifname_split.groups())
        if max((fpc, pic, port_index)) > 254:
            return "Other"

        if "pic" not in self.cache:
            self.cache["pic"] = {}

        if (fpc, pic) not in self.cache["pic"]:
            try:
                chassis_pic_xml = self.device._rpc(
                    self._gen_rpc_request_pic_info(fpc, pic)
                )
            except RpcError as e:
                logger.debug("RPC error: %s", e)
                raise TypeCouldNotBeParsedError(interface)

            parsed_xml = defusedxml.lxml.fromstring(chassis_pic_xml)
            self.cache["pic"][(fpc, pic)] = parsed_xml
        else:
            parsed_xml = self.cache["pic"][(fpc, pic)]

        try:
            ports_info = parsed_xml.findall(".//port-information")[0]
        except IndexError:
            return parsed_xml.findall(".//pic-type")[0].text

        for p in ports_info.getchildren():
            if int(p.xpath("port-number")[0].text) == port_index:
                return p.xpath("sfp-vendor-pno")[0].text

        raise TypeCouldNotBeParsedError(interface)

    def _gen_rpc_request_pic_info(self, fpc, pic):
        get_pic_details_el = lxml.etree.Element("get-pic-detail")
        xml_tree = get_pic_details_el.getroottree()

        for slot_type in ("fpc", "pic"):
            slot_el = lxml.etree.Element("{}-slot".format(slot_type))
            get_pic_details_el.append(slot_el)
            slot_el.text = str(vars()[slot_type])

        return lxml.etree.tostring(xml_tree).decode()

    def get_detailed_lldp_neighbours(self):
        try:
            lldp_neighbours_xml = self.device._rpc(
                self._gen_rpc_lldp_neighbours()
            )
        except RpcError as e:
            logger.debug("RPC error: %s", e)
            raise

        parsed_xml = defusedxml.lxml.fromstring(lldp_neighbours_xml)

        for n in parsed_xml.xpath(".//lldp-neighbor-information"):
            yield {
                "local_port": (
                    n.xpath(
                        "lldp-local-interface"
                    )[0].text.split(".")[0].strip()
                ),
                "hostname": (
                    n.xpath("lldp-remote-system-name")[0].text.strip()
                ),
                "port": (
                    n.xpath(
                        "lldp-remote-port-description"
                    )[0].text.split(".")[0].strip()
                ),
                "chassis_id": (
                    n.xpath("lldp-remote-chassis-id")[0].text.strip()
                ),
            }

    def _gen_rpc_lldp_neighbours(self):
        get_lldp_neighbours_el = lxml.etree.Element(
            "get-lldp-neighbors-information"
        )
        xml_tree = get_lldp_neighbours_el.getroottree()

        return lxml.etree.tostring(xml_tree).decode()
