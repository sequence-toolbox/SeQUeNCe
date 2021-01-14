import json5

from .topology import Topology as Topo
from .node import QKDNode
from ..kernel.timeline import Timeline


class QKDTopo(Topo):
    """Class for managing network topologies.

    The topology class provies a simple interface for managing the nodes and connections in a network.
    A network may also be generated using an external json file.

    Attributes:
        name (str): label for topology.
        timeline (Timeline): timeline to be used for all objects in network.
        nodes (Dict[str, Node]): mapping of node names to node objects.
        qchannels (List[QuantumChannel]): list of quantum channel objects in network.
        cchannels (List[ClassicalChannel]): list of classical channel objects in network.
        graph: (Dict[str, Dict[str, float]]): internal representation of quantum graph.
    """
    QKD_NODE = "QKDNode"

    def __init__(self, conf_file_name: str):
        """Constructor for topology class.

        Args:
            name (str): label for topology.
            timeline (Timeline): timeline for simulation.
        """
        super().__init__(conf_file_name)

    def _load(self, filename):
        topo_config = json5.load(open(filename))
        self._add_timeline(topo_config)
        self._add_nodes(topo_config)
        self._add_qchannels(topo_config)
        self._add_cchannels(topo_config)
        self._add_cconnections(topo_config)

    def _add_timeline(self, config):
        stop_time = config.get(Topo.STOP_TIME, float('inf'))
        self.tl = Timeline(stop_time)

    def _add_nodes(self, config):
        for node in config[Topo.ALL_NODE]:
            type = node[Topo.TYPE]
            if type == self.QKD_NODE:
                name = node[Topo.NAME]
                # only support set the name of QKD node
                # could be extended in the future
                node = QKDNode(name, self.tl)

            else:
                raise NotImplementedError("Unknown type of node")
            if type in self.nodes:
                self.nodes[type].append(node)
            else:
                self.nodes[type] = [node]
