import logging
from netboxapi import NetboxAPI, NetboxMapper
from ocs.conf import get_config


logger = logging.getLogger("netbox_importer")


class NetboxPusher():
    _device = None

    def __init__(self, hostname, props):
        self.netbox_api = NetboxAPI(**get_config("ocs").get("netbox"))
        self.hostname = hostname
        self.props = props

        self._mappers = {
            "dcim_choices": NetboxMapper(
                self.netbox_api, app_name="dcim", model="_choices"
            ), "devices": NetboxMapper(
                self.netbox_api, app_name="dcim", model="devices"
            ), "interfaces": NetboxMapper(
                self.netbox_api, app_name="dcim", model="interfaces"
            ), "ip": NetboxMapper(
                self.netbox_api, app_name="ipam", model="ip-addresses"
            )
        }
        self._choices_cache = {}

    def push(self):
        # XXX: raise an exception if device not found
        self._device = next(self._mappers["devices"].get(name=self.hostname))
        self._push_interfaces()
        self._push_main_data()

    def _push_interfaces(self):
        interfaces_props = self.props["interfaces"]
        interfaces_lag = {}
        interfaces = {}

        for if_name, if_prop in interfaces_props.items():
            if_prop = if_prop.copy()
            interface_query = self._mappers["interfaces"].get(
                device_id=self._device, name=if_name
            )
            try:
                interface = next(interface_query)
            except StopIteration:
                interface = self._mappers["interfaces"].post(
                    device=self._device, name=if_name
                )
            interfaces[if_name] = interface

            if_type = if_prop.pop("type")
            if_prop["form_factor"] = self.search_value_in_choices(
                self._mappers["dcim_choices"], "interface:form_factor",
                if_type
            )
            if if_prop.get("lag"):
                interfaces_lag[if_name] = if_prop.pop("lag")

            for k, v in if_prop.items():
                setattr(interface, k, v)

            interface.put()
            if if_prop.get("ip"):
                self._attach_interface_to_ip_addresses(
                    interface, *if_prop["ip"]
                )

        self._update_interfaces_lag(interfaces, interfaces_lag)

    def _attach_interface_to_ip_addresses(self, interface, *ip_addresses):
        mapper = self._mappers["ip"]

        for ip in ip_addresses:
            try:
                ip_netbox_obj = next(mapper.get(q=ip))
            except StopIteration:
                ip_netbox_obj = mapper.post(address=ip)

            # XXX: handle anycast
            ip_netbox_obj.interface = interface
            ip_netbox_obj.put()

    def _update_interfaces_lag(self, interfaces, interfaces_lag):
        """
        :param interfaces: {interface_name: netbox_interface_obj, …}
        """
        for if_name, lag in interfaces_lag.items():
            interface = interfaces[if_name]
            interface.lag = interfaces[lag]
            interface.put()

    def _push_main_data(self):
        mapper = self._mappers["ip"]
        if self.props.get("serial"):
            self._device.serial = self.props["serial"]

        for ip_key in ("primary_ip4", "primary_ip6"):
            ip = self.props.get(ip_key)
            if ip:
                try:
                    ip_netbox_obj = next(mapper.get(q=ip))
                    setattr(self._device, ip_key, ip_netbox_obj)
                except StopIteration:
                    logger.error(
                        "Cannot set primary IP %s as it does not exist in "
                        "netbox", ip
                    )

        self._device.put()

    def search_value_in_choices(self, mapper, id, label):
        if mapper not in self._choices_cache:
            try:
                self._choices_cache[mapper] = next(mapper.get())
            except StopIteration:
                pass

        for choice in self._choices_cache[mapper][id]:
            if choice["label"] == label:
                return choice["value"]

        raise KeyError("Label {} not in choices".format(label))
