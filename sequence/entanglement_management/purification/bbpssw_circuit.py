"""Code for BBPSSW entanglement purification using the circuit formalism.

This module defines code to support the BBPSSW protocol for entanglement purification.
Success results are pre-determined based on network parameters.
Also defined is the message type used by the BBPSSW code.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from ...components.circuit import Circuit

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node

from ...utils import log
from ...constants import KET_STATE_FORMALISM, DENSITY_MATRIX_FORMALISM
from .bbpssw_protocol import BBPSSWProtocol, BBPSSWMessage, BBPSSWMsgType

@BBPSSWProtocol.register(KET_STATE_FORMALISM)
@BBPSSWProtocol.register(DENSITY_MATRIX_FORMALISM)
class BBPSSWCircuit(BBPSSWProtocol):
    """Purification protocol instance.

    This class provides an implementation of the BBPSSW purification protocol.
    It should be instantiated on a quantum router node.

    Variables:
        BBPSSW.circuit (Circuit): circuit that purifies entangled memories.

    Attributes:
        owner (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        kept_memo: memory to be purified by the protocol (should already be entangled).
        meas_memo: memory to measure and discart (should already be entangled).
        meas_res (int): measurement result from circuit.
        remote_node_name (str): name of other node.
        remote_protocol_name (str): name of other protocol
        remote_memories (list[str]): name of remote memories
    """

    circuit = Circuit(2)
    circuit.cx(0, 1)
    circuit.measure(1)

    def __init__(self, owner: "Node", name: str, kept_memo: "Memory", meas_memo: "Memory"):
        """Constructor for purification protocol.

        args:
            owner (Node): Node the protocol of which the protocol is attached.
            name (str): Name of protocol instance.
            kept_memo (Memory): Memory to keep and improve the fidelity.
            meas_memo (Memory): Memory to measure and discard.
        """
        super().__init__(owner, name, kept_memo, meas_memo)

    def start(self) -> None:
        """Method to start entanglement purification.

        Run the circuit below on two pairs of entangled memories on both sides of protocol.

        o -------(x)----------| M |
        .         |
        .   o ----.----------------
        .   .
        .   .
        .   o
        .
        o

        The overall circuit is shown below:

         o -------(x)----------| M |
         .         |
         .   o ----.----------------
         .   .
         .   .
         .   o ----.----------------
         .         |
         o -------(x)----------| M |

        Side Effects:
            May update parameters of kept memory.
            Will send message to other protocol instance.
        """
        super().start()
        meas_samp = self.owner.get_generator().random()
        self.meas_res = self.owner.timeline.quantum_manager.run_circuit(
            self.circuit, [self.kept_memo.qstate_key,
                           self.meas_memo.qstate_key],
            meas_samp)
        self.meas_res = self.meas_res[self.meas_memo.qstate_key]
        dst = self.kept_memo.entangled_memory["node_id"]

        message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES,
                                self.remote_protocol_name,
                                meas_res=self.meas_res)
        self.owner.send_message(dst, message)

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        """Method to receive messages.

        args:
            src (str): name of node that sent the message.
            msg (BBPSSW message): message received.

        Side Effects:
            Will call `update_resource_manager` method.
        """

        log.logger.info(
            self.owner.name + " received result message, succeeded: {}".format(
                self.meas_res == msg.meas_res))
        assert src == self.remote_node_name

        self.update_resource_manager(self.meas_memo, "RAW")
        if self.meas_res == msg.meas_res:
            self.kept_memo.fidelity = self.improved_fidelity(self.kept_memo.fidelity)
            self.update_resource_manager(self.kept_memo, state="ENTANGLED")
        else:
            self.update_resource_manager(self.kept_memo, state="RAW")

    @staticmethod
    @lru_cache(maxsize=128)
    def improved_fidelity(f: float) -> float:
        """Method to calculate fidelity after purification.

        Formula comes from Dur and Briegel (2007) formula (18) page 14.

        Args:
            f (float): fidelity of entanglement.
        """

        return (f ** 2 + ((1 - f) / 3) ** 2) / (f ** 2 + 2 * f * (1 - f) / 3 + 5 * ((1 - f) / 3) ** 2)
