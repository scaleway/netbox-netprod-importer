import collections
import logging
from netbox_netprod_importer.exceptions import MissingGraphError


logger = logging.getLogger("netbox_importer")


def build_graph_from_lldp(importers):
    graph = NetworkConnections()
    for host, importer in importers.items():
        host_node = graph.get_new_node(host)

        for port, port_neighbours in importer.get_lldp_neighbours().items():
            for neighbour in port_neighbours:
                neighbour_node = graph.get_or_create(neighbour["hostname"])
                host_node.add_neighbour(
                    port, neighbour_node, neighbour["port"]
                )


class NetworkConnections():
    #: nodes by hostname
    nodes = None

    def __init__(self):
        self.nodes = {}

    def add(self, node):
        if node.hostname in self.nodes:
            raise ValueError("{} already in nodes".format(node.hostname))

        self.nodes[node.hostname] = node
        node.graph = self

    def pop(self, hostname):
        node = self.nodes.pop(hostname)
        node.detach_from_current_graph()

        return node

    def get_new_node(self, hostname):
        node = NetworkNode(graph=self, hostname=hostname)
        self.add(node)

        return node

    def get_or_create(self, hostname):
        if hostname in self.nodes:
            return self.nodes[hostname]

        node = self.get_new_node(hostname)
        self.add(node)
        return node

    def __iter__(self):
        yield from self.nodes.values()


class NetworkNode():
    neighbours = None

    def __init__(self, graph, hostname, neighbours=None):
        self._graph = graph
        self._hostname = hostname

        if neighbours is None:
            neighbours = collections.defaultdict(set)
        self.neighbours = neighbours

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, hostname):
        if self._graph:
            self._graph.nodes[hostname] = self
            try:
                self._graph.nodes.pop(self._hostname)
            except KeyError:
                logger.error(
                    "{} not found in graph's nodes".format(self._hostname)
                )

        self._hostname = hostname
        return self._hostname

    def add_neighbour(self, port, node, node_port):
        self.neighbours[port].append(node)
        node.neighbours[node_port].append(self)

    def remove_neighbour(self, port, node):
        self.neighbours[port].remove(node)
        neighbour_port = node.search_neighbour(self)
        node.remove_neighbour(neighbour_port, self)

    def search_neighbour(self, neighbour):
        for port, port_neighbours in self.neighbours.items():
            if neighbour in port_neighbours:
                return port

        raise ValueError("node not a neighbour")

    def detach_from_current_graph(self):
        if not self._graph:
            raise MissingGraphError(
                "Cannot detach from current graph is no graph is attached"
            )

        self._graph = None
