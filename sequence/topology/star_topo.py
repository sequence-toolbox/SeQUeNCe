"""Definition of the StarTopo class.

StarTopo is a child class of Topology that provides a base for
implementing star-style topologies (via inheritance)

Subclasses: QlanStarTopo (I don't know if there will even be more in the future)
"""
from abc import abstractmethod

from .topology import Topology
from ..constants import *


class StarTopo(Topology):
    """Subclasses MUST define:
        _add_nodes()
        _add_protocols()

    No Attributes.
    """

    def _build(self, config: dict):
        self._add_parameters(config)

        # quantum connections are only supported by sequential simulation so far
        self._add_qconnections(config)

        self._add_timeline(config)
        self._add_nodes(config)
        self._add_qchannels(config)
        self._add_cchannels(config)
        self._add_cconnections(config)
        self._add_protocols()

    def _add_parameters(self, config: dict):
        """Hook for subclasses to extract config parameters. No-op by default."""
        pass

    @abstractmethod
    def _add_nodes(self, config: dict):
        pass

    @abstractmethod
    def _add_protocols(self):
        pass

    def _add_qconnections(self, config: dict):
        '''generate bsm_info, qc_info, and cc_info for the q_connections
        '''
        for q_connect in config.get(ALL_Q_CONNECT, []):
            node1 = q_connect[CONNECT_NODE_1]
            node2 = q_connect[CONNECT_NODE_2]
            attenuation = q_connect[ATTENUATION]
            distance = q_connect[DISTANCE] // 2
            channel_type = q_connect[TYPE]
            cc_delay = self._calc_cc_delay(config, node1, node2)
