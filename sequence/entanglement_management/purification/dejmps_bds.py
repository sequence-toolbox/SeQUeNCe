"""Code for DEJMPS entanglement purification with Bell diagonal states."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .bbpssw_bds import BBPSSW_BDS
from .bbpssw_protocol import BBPSSWProtocol

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node


DEJMPS_BDS_PROTOCOL = "dejmps_bds"


@BBPSSWProtocol.register(DEJMPS_BDS_PROTOCOL)
class DEJMPS_BDS(BBPSSW_BDS):
    """DEJMPS purification protocol for Bell diagonal states.

    This class exposes the non-twirled Bell diagonal purification path as a
    first-class protocol. It reuses the BBPSSW_BDS protocol lifecycle while
    preserving the full Bell diagonal coefficient vector.
    """

    def __init__(self, owner: Node, name: str, kept_memo: Memory, meas_memo: Memory):
        """Constructor for the DEJMPS BDS purification protocol.

        Args:
            owner (Node): Node the protocol is attached to.
            name (str): Name of protocol instance.
            kept_memo (Memory): Memory to keep and improve.
            meas_memo (Memory): Memory to measure and discard.
        """
        super().__init__(owner, name, kept_memo, meas_memo, is_twirled=False)
        self.protocol_type = DEJMPS_BDS_PROTOCOL
