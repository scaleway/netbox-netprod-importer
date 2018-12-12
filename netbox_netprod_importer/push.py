from abc import ABC, abstractmethod
from collections import defaultdict
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import logging
from requests.exceptions import HTTPError
import threading

import cachetools
from netboxapi import NetboxMapper
from tqdm import tqdm

from netbox_netprod_importer.vendors.cisco import CiscoParser
from netbox_netprod_importer.vendors.juniper import JuniperParser
from netbox_netprod_importer.exceptions import (
    DeviceNotFoundError, NetInterfaceNotFoundError, IPPushingError,
    NetIfPushingError
)
from netbox_netprod_importer.tools import is_macaddr, macaddr_to_int


logger = logging.getLogger("netbox_importer")


class _NetboxPusher(ABC):

    def __init__(self, netbox_api, *args, **kwargs):
        self.netbox_api = netbox_api

        self._mappers = {
            "dcim_choices": NetboxMapper(
                self.netbox_api, app_name="dcim", model="_choices"
            ), "devices": NetboxMapper(
                self.netbox_api, app_name="dcim", model="devices"
            ), "interfaces": NetboxMapper(
                self.netbox_api, app_name="dcim", model="interfaces"
            ), "interface-connections": NetboxMapper(
                self.netbox_api, app_name="dcim", model="interface-connections"
            ), "ip": NetboxMapper(
                self.netbox_api, app_name="ipam", model="ip-addresses"
            )
        }
        self._choices_cache = {}

    @abstractmethod
    def push(self):
        pass

    def search_value_in_choices(self, mapper_name, id, label):
        if mapper_name not in self._choices_cache:
            try:
                mapper = self._mappers[mapper_name]
                self._choices_cache[mapper_name] = next(mapper.get())
            except StopIteration:
                pass

        for choice in self._choices_cache[mapper_name][id]:
            if choice["label"] == label:
                return choice["value"]

        raise KeyError("Label {} not in choices".format(label))


class NetboxDevicePropsPusher(_NetboxPusher):
    _device = None

    def __init__(self, netbox_api, hostname, props, *args, overwrite=False,
                 **kwargs):
        super().__init__(netbox_api, *args, **kwargs)

        self.hostname = hostname
        self.props = props
        self.overwrite = overwrite

    def push(self):
        # XXX: raise an exception if device not found
        self._device = next(self._mappers["devices"].get(name=self.hostname))
        if self.overwrite:
            self._clean_unmatched_interfaces()
        self._push_interfaces()
        self._push_main_data()

    def _clean_unmatched_interfaces(self):
        pushed_interfaces = self._mappers["interfaces"].get(
            device_id=self._device
        )

        for netbox_if in pushed_interfaces:
            if netbox_if.name not in self.props["interfaces"]:
                self._clean_attached_ip(netbox_if)
                netbox_if.delete()

    def _clean_attached_ip(self, netbox_if):
        attached_addrs = self._mappers["ip"].get(interface_id=netbox_if)
        for a in attached_addrs:
            a.delete()

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
                try:
                    interface = self._mappers["interfaces"].post(
                        device=self._device, name=if_name
                    )
                except HTTPError as e:
                    raise NetIfPushingError(if_name, e)

            interfaces[if_name] = interface

            if_type = if_prop.pop("type")
            if_prop["form_factor"] = self.search_value_in_choices(
                "dcim_choices", "interface:form_factor",
                if_type
            )
            if if_prop.get("lag"):
                interfaces_lag[if_name] = if_prop.pop("lag")

            if not self.overwrite and "mode" in if_prop:
                if_prop.pop("mode")
            elif if_prop.get("mode"):
                # cannot really guess (yet) the interface mode, so only set it
                # if overwrite
                self._handle_interface_mode(interface, if_prop["mode"])
                if_prop.pop("mode")

            for k, v in if_prop.items():
                setattr(interface, k, v)

            try:
                interface.put()
            except HTTPError as e:
                raise NetIfPushingError(interface.name, e)
            if if_prop.get("ip"):
                addrs = self._attach_interface_to_ip_addresses(
                    interface, *if_prop["ip"]
                )
                if self.overwrite:
                    self._clean_unmatched_ip_addresses(interface, *addrs)

        self._update_interfaces_lag(interfaces, interfaces_lag)

    def _handle_interface_mode(self, netbox_if, mode):
        netbox_mode = self.search_value_in_choices(
            "dcim_choices", "interface:mode",
            mode
        )

        netbox_if.mode = netbox_mode

    def _attach_interface_to_ip_addresses(self, netbox_if, *ip_addresses):
        mapper = self._mappers["ip"]

        addresses = []
        for ip in ip_addresses:
            # check if ip attached isn't already correct
            try:
                ip_netbox_obj = next(mapper.get(q=ip, interface_id=netbox_if))
            except StopIteration:
                try:
                    ip_netbox_obj = next(mapper.get(q=ip))
                except StopIteration:
                    try:
                        ip_netbox_obj = mapper.post(address=ip)
                    except HTTPError as e:
                        raise IPPushingError(ip, e)

                # XXX: handle anycast
                ip_netbox_obj.interface = netbox_if
                try:
                    ip_netbox_obj.put()
                except HTTPError as e:
                    raise IPPushingError(ip_netbox_obj.address, e)

            addresses.append(ip_netbox_obj)

        return addresses

    def _clean_unmatched_ip_addresses(self, netbox_if, *netbox_ip):
        attached_addrs = self._mappers["ip"].get(interface_id=netbox_if)
        netbox_ip_ids = set(obj.id for obj in netbox_ip)

        for addr in attached_addrs:
            if addr.id not in netbox_ip_ids:
                addr.delete()

    def _update_interfaces_lag(self, interfaces, interfaces_lag):
        """
        :param interfaces: {interface_name: netbox_interface_obj, …}
        """
        for if_name, lag in interfaces_lag.items():
            interface = interfaces[if_name]
            interface.lag = interfaces[lag]
            try:
                interface.put()
            except HTTPError as e:
                raise NetIfPushingError(interface.name, e)

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


class NetboxInterconnectionsPusher(_NetboxPusher):
    """
    Push in Netbox a graph representing the interconnections between devices
    """

    def __init__(self, *args, remove_domains=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.remove_domains = remove_domains or []
        self.interfaces_cache = cachetools.LRUCache(128)
        self._lock = threading.Lock()

    def push(self, importers, threads=1):
        result = {"done": 0, "errors_interco": 0, "errors_device": 0}

        importers = importers.copy()
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {}
            queue = set()
            for host, importer in importers.items():
                future = executor.submit(
                    self._handle_device, host, importer, queue
                )
                futures[future] = host

            futures_with_progress = tqdm(
                concurrent.futures.as_completed(futures),
                total=len(futures)
            )
            for future in futures_with_progress:
                host = futures[future]
                try:
                    task_result = future.result()
                    result["done"] += task_result["done"]
                    result["errors_interco"] += task_result["errors"]
                except ValueError:
                    logger.debug(
                        "LLDP parsing not supported on {}".format(host)
                    )
                    result["errors_device"] += 1
                except Exception as e:
                    logger.debug(
                        "Error when defining interconnections on host %s: %s",
                        host, e
                    )
                    result["errors_device"] += 1
                importers.pop(host)

        return result

    def _handle_device(self, hostname, importer, queue):
        result = {"done": 0, "errors": 0}
        with importer:
            for interco in importer.get_lldp_neighbours():
                hashable_interco = tuple(sorted((
                    interco["hostname"], importer.hostname,
                    interco["local_port"], interco["port"]
                )))
                if hashable_interco in queue:
                    continue

                try:
                    queue.add(hashable_interco)

                    try:
                        self._interconnect_using_lldp_names(
                            hostname, importer, interco
                        )
                    except DeviceNotFoundError:
                        if "chassis_id" not in interco:
                            raise

                        self._interconnect_using_lldp_id(
                            hostname, importer, interco
                        )

                    result["done"] += 1
                except Exception as e:
                    result["errors"] += 1
                    logger.debug("Error with interco %s: %s", interco, e)
                    continue

        return result

    def _interconnect_using_lldp_names(self, hostname, importer, interco):
        a = hostname
        netif_a = self._get_netif_or_derivative(a, interco["local_port"])
        b = interco["hostname"]

        for dom in self.remove_domains:
            dom = "." + dom.lstrip(".").rstrip(".")
            if b.endswith(dom):
                b = b.rstrip(dom)
                break

        netif_b = self._get_netif_or_derivative(b, interco["port"])

        with self._lock:
            # force a refresh of the interfaces
            netif_a = next(netif_a.get())
            netif_b = next(netif_b.get())
            self.interconnect_netbox_netif(netif_a, netif_b)

    def _interconnect_using_lldp_id(self, hostname, importer, interco):
        a = hostname
        netif_a = self._get_netif_or_derivative(a, interco["local_port"])
        netif_b = self._find_netbox_netif_from_lldp_id(
            interco["chassis_id"], interco["port"]
        )

        with self._lock:
            # force a refresh of the interfaces
            netif_a = next(netif_a.get())
            netif_b = next(netif_b.get())
            self.interconnect_netbox_netif(netif_a, netif_b)

    def _find_netbox_netif_from_lldp_id(self, lldp_id, if_name):
        """
        Find an interface in netbox from a LLDP ID and its name

        LLDP ID is usually the mac address of one interface of our device. Look
        for it in netbox, then search the if_name
        """
        try:
            some_device_netif = next(
                self._mappers["interfaces"].get(mac_address=lldp_id)
            )
        except StopIteration:
            raise NetInterfaceNotFoundError(lldp_id)

        device = some_device_netif.device
        return self._get_netif_or_derivative(device.name, if_name)

    def interconnect_netbox_netif(self, netif_a, netif_b):
        props = {
            "interface_a": netif_a,
            "interface_b": netif_b,
            "connection_status": True
        }

        netif_connection = None
        if netif_b.interface_connection:
            connected_netif_id = int(
                netif_b.interface_connection["interface"]["id"]
            )
            if connected_netif_id == netif_a.id:
                return
            elif netif_a.interface_connection:
                self._delete_connection_to_netbox_netif(netif_b)
                # force a refresh to clear attached connections
                netif_b = next(netif_b.get())
            else:
                netif_connection = self._get_current_interco_of_netif(netif_b)

        if netif_a.interface_connection:
            netif_connection = self._get_current_interco_of_netif(netif_a)

        if netif_connection:
            for k, v in props.items():
                setattr(netif_connection, k, v)

            netif_connection.put()
        else:
            netif_connection = self._mappers["interface-connections"].post(
                **props
            )

        return netif_connection

    def _get_current_interco_of_netif(self, netif):
        if netif.interface_connection.get("id"):
            return next(self._mappers["interface-connections"].get(
                netif.interface_connection["id"]
            ))
        else:
            netif_connections = self._mappers["interface-connections"].get(
                device=netif.device.name
            )
            return self._find_connection_in_netif_connections(
                netif_connections, netif
            )

    def _delete_connection_to_netbox_netif(self, netif):
        connections = self._mappers["interface-connections"].get(
            device=netif.device.name
        )
        netif_connection = self._find_connection_in_netif_connections(
            connections, netif
        )
        netif_connection.delete()

    def _find_connection_in_netif_connections(self, netif_connections, netif):
        for c in netif_connections:
            if c.interface_a.id == netif.id or c.interface_b.id == netif.id:
                return c

        raise ValueError(
            "No connection found for network interface {}".format(netif.id)
        )

    def _get_netif_or_derivative(self, hostname, netif):
        """
        Get netif or derivative names of hostname

        netif can be a macaddr, but to be conservative, it will only work if
        only one interface has this macaddr.
        """
        interfaces = self._get_interfaces_for_device(hostname)

        if netif in interfaces:
            return interfaces[netif]

        if is_macaddr(netif):
            mac_addresses = defaultdict(list)
            for i in interfaces:
                mac_addresses[macaddr_to_int(i.mac_address)].append(i)

            int_netif_mac = macaddr_to_int(netif)
            if mac_addresses.get(int_netif_mac, 0) == 1:
                return mac_addresses[int_netif_mac]
        else:
            for netif_deriv in self._get_all_derivatives_for_netif(netif):
                for k in interfaces:
                    for i in self._get_all_derivatives_for_netif(k):
                        if i == netif_deriv:
                            return interfaces[k]

        raise ValueError(
            "Interface {} not found".format(netif)
        )

    def _get_interfaces_for_device(self, hostname):
        interfaces = self.interfaces_cache.get(hostname)
        if interfaces is not None:
            return interfaces

        try:
            device = next(self._mappers["devices"].get(name=hostname))
        except StopIteration:
            raise DeviceNotFoundError(hostname)

        interfaces = {
            netif.name: netif
            for netif in self._mappers["interfaces"].get(device_id=device.id)
        }
        self.interfaces_cache[hostname] = interfaces

        return interfaces

    def _get_all_derivatives_for_netif(self, netif):
        yield netif
        yield CiscoParser.get_abrev_if(netif)
        yield JuniperParser.get_real_ifname(netif)
