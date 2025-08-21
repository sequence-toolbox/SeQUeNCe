from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...components.bsm import SingleAtomBSM
    from ...topology.node import Node, BSMNode
    from ...components.memory import Memory

from .generation_message import EntanglementGenerationMessage, GenerationMsgType
from ..entanglement_protocol import EntanglementProtocol
from ..generation.generation_a_bk import EntanglementGenerationBarretKokA


class EntanglementGenerationBarretKokB(EntanglementProtocol):
    """Entanglement generation protocol for BSM node.

    The EntanglementGenerationB protocol should be instantiated on a BSM node.
    Instances will communicate with the A instance on neighboring quantum router nodes to generate entanglement.

    Attributes:
        owner (BSMNode): node that protocol instance is attached to.
        name (str): label for protocol instance.
        others (list[str]): list of neighboring quantum router nodes
    """

    def __init__(self, owner: "BSMNode", name: str, others: list[str]):
        """Constructor for entanglement generation B protocol.

        Args:
            owner (Node): attached node.
            name (str): name of protocol instance.
            others (list[str]): name of protocol instance on end nodes.
        """

        super().__init__(owner, name)
        assert len(others) == 2
        self.others = others  # end nodes

    def bsm_update(self, bsm: "SingleAtomBSM", info: dict[str, Any]):
        """Method to receive detection events from BSM on node.

        Args:
            bsm (SingleAtomBSM): bsm object calling method.
            info (dict[str, any]): information passed from bsm.
        """

        assert info['info_type'] == "BSM_res"

        res = info["res"]
        time = info["time"]
        resolution = bsm.resolution

        for node in self.others:
            message = EntanglementGenerationMessage(GenerationMsgType.MEAS_RES,
                                                    receiver=None, # receiver is None (not paired)
                                                    protocol_type=EntanglementGenerationBarretKokA,
                                                    detector=res,
                                                    time=time,
                                                    resolution=resolution)
            self.owner.send_message(node, message)

    def received_message(self, src: str, msg: EntanglementGenerationMessage):
        raise Exception(f'EntanglementGenerationB protocol {self.name} should not receive message;.')

    def start(self) -> None:
        pass

    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        pass

    def is_ready(self) -> bool:
        return True

    def memory_expire(self, memory: "Memory") -> None:
        raise Exception(f'Memory expire called for EntanglementGenerationB protocol {self.name}')