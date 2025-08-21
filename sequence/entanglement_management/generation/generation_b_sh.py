from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ...components.bsm import SingleAtomBSM
    from ...topology.node import Node, BSMNode
    from ...components.memory import Memory

from .generation_message import EntanglementGenerationMessage, GenerationMsgType
from ..entanglement_protocol import EntanglementProtocol

class EntanglementGenerationSingleHeraldedB(EntanglementProtocol):
    def __init__(self, owner: "BSMNode", name: str, others: List[str]):
        super().__init__(owner, name)
        assert len(others) == 2
        self.others = others

    def bsm_update(self, bsm, info: Dict['str', Any]) -> None:
        """Method to receive detection events from BSM on node.

        Args:
            bsm (SingleAtomBSM or SingleHeraldedBSM): bsm object calling method.
            info (Dict[str, any]): information passed from bsm.
        """
        assert bsm.encoding == 'single_heralded', \
            "EntanglementGenerationSingleHeraldedB should only be used with SingleHeraldedBSM."

        assert info['info_type'] == "BSM_res"

        res = info['res']
        time = info['time']
        resolution = info['resolution']

        for i, node in enumerate(self.others):
            message = EntanglementGenerationMessage(
                GenerationMsgType.MEAS_RES,
                receiver=None,
                protocol_type=self,
                detector=res,
                time=time,
                resolution=resolution
            )
            self.owner.send_message(node, message)

    def received_message(self, src: str, msg: EntanglementGenerationMessage) -> None:
        raise Exception(f'EntanglementGenerationSingleHeraldedB protocol {self.name} should not receive message;.')

    def start(self) -> None:
        pass

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        pass

    def is_ready(self) -> bool:
        return True

    def memory_expire(self, memory: "Memory") -> None:
        raise Exception(f'EntanglementGenerationSingleHeraldedB protocol {self.name} should not receive memory expiration;.')

