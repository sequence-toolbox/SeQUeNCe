"""Code for entanglement swapping.

This module defines code for entanglement swapping.
Success is pre-determined based on network parameters.
The entanglement swapping protocol is an asymmetric protocol:

* The EntanglementSwappingA instance initiates the protocol and performs the swapping operation.
* The EntanglementSwappingB instance waits for the swapping result from EntanglementSwappingA.

The swapping results decides the following operations of EntanglementSwappingB.
Also defined in this module is the message type used by these protocols.
"""


from __future__ import annotations
from typing import TYPE_CHECKING
from functools import lru_cache

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node

from .swapping_base import EntanglementSwappingA, EntanglementSwappingB, SwappingMsgType, EntanglementSwappingMessage
from ...components.circuit import Circuit
from ...constants import KET_VECTOR_FORMALISM, DENSITY_MATRIX_FORMALISM
from ...resource_management.memory_manager import MemoryInfo
from ...utils import log


@EntanglementSwappingA.register(KET_VECTOR_FORMALISM)
@EntanglementSwappingA.register(DENSITY_MATRIX_FORMALISM)
class EntanglementSwappingA_Circuit(EntanglementSwappingA):
    """Entanglement swapping protocol for middle router.

    The entanglement swapping protocol is an asymmetric protocol.
    EntanglementSwappingA_Circuit should be instantiated on the middle node, where it measures a memory from each pair to be swapped.
    Results of measurement and swapping are sent to the end routers.

    Variables:
        EntanglementSwappingA_Circuit.circuit (Circuit): circuit that does swapping operations.

    Attributes:
        owner (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
        left_memo (Memory): a memory from one pair to be swapped.
        right_memo (Memory): a memory from the other pair to be swapped.
        left_node (str): name of node that contains memory entangling with left_memo.
        left_remote_memo (str): name of memory that entangles with left_memo.
        right_node (str): name of node that contains memory entangling with right_memo.
        right_remote_memo (str): name of memory that entangles with right_memo.
        success_prob (float): probability of a successful swapping operation.
        degradation (float): degradation factor of memory fidelity after swapping.
        is_success (bool): flag to show the result of swapping
        left_protocol_name (str): name of left protocol.
        right_protocol_name (str): name of right protocol.
    """

    circuit = Circuit(2)
    circuit.cx(0, 1)
    circuit.h(0)
    circuit.measure(0)
    circuit.measure(1)

    def __init__(self, owner: Node, name: str, left_memo: Memory, right_memo: Memory, success_prob=1, degradation=0.95):
        """Constructor for entanglement swapping A protocol.

        Args:
            owner (Node): node that protocol instance is attached to.
            name (str): label for swapping protocol instance.
            left_memo (Memory): memory entangled with a memory on one distant node.
            right_memo (Memory): memory entangled with a memory on the other distant node.
            success_prob (float): probability of a successful swapping operation (default 1).
            degradation (float): degradation factor of memory fidelity after swapping (default 0.95).
        """
        assert left_memo != right_memo
        super().__init__(owner, name, left_memo, right_memo, success_prob)
        self.degradation = degradation

    def start(self) -> None:
        """Method to start entanglement swapping protocol.

        Will run circuit and send measurement results to other protocols.

        Side Effects:
            Will call `update_resource_manager` method.
            Will send messages to other protocols.
        """

        log.logger.info(f"{self.owner.name} middle protocol start with ends {self.left_node}, {self.right_node}")

        assert self.left_memo.fidelity > 0 and self.right_memo.fidelity > 0
        assert self.left_memo.entangled_memory["node_id"] == self.left_node
        assert self.right_memo.entangled_memory["node_id"] == self.right_node

        if self.owner.get_generator().random() < self.success_probability():
            # swapping succeeded
            fidelity = self.updated_fidelity(self.left_memo.fidelity, self.right_memo.fidelity)
            self.is_success = True

            expire_time = min(self.left_memo.get_expire_time(), self.right_memo.get_expire_time())

            meas_samp = self.owner.get_generator().random()
            meas_res = self.owner.timeline.quantum_manager.run_circuit(
                        self.circuit, [self.left_memo.qstate_key, self.right_memo.qstate_key], meas_samp)
            meas_res = [meas_res[self.left_memo.qstate_key], meas_res[self.right_memo.qstate_key]]
            
            log.logger.info(f"{self.name} swapping succeeded, meas_res={meas_res[0]},{meas_res[1]}")
            
            msg_l = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES,
                                                self.left_protocol_name, fidelity=fidelity,
                                                remote_node=self.right_memo.entangled_memory["node_id"],
                                                remote_memo=self.right_memo.entangled_memory["memo_id"],
                                                expire_time=expire_time, meas_res=[])  # empty meas_res
            msg_r = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES, 
                                                self.right_protocol_name, fidelity=fidelity,
                                                remote_node=self.left_memo.entangled_memory["node_id"],
                                                remote_memo=self.left_memo.entangled_memory["memo_id"],
                                                expire_time=expire_time, meas_res=meas_res)
        else:
            # swapping failed
            log.logger.info(f"{self.name} swapping failed")
            msg_l = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES,self.left_protocol_name, fidelity=0)
            msg_r = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES, self.right_protocol_name, fidelity=0)

        self.owner.send_message(self.left_node, msg_l)
        self.owner.send_message(self.right_node, msg_r)

        self.update_resource_manager(self.left_memo, MemoryInfo.RAW)
        self.update_resource_manager(self.right_memo, MemoryInfo.RAW)

    @lru_cache(maxsize=128)
    def updated_fidelity(self, f1: float, f2: float) -> float:
        """A simple model updating fidelity of entanglement.

        Args:
            f1 (float): fidelity 1.
            f2 (float): fidelity 2.

        Returns:
            float: fidelity of swapped entanglement.
        """

        return f1 * f2 * self.degradation


@EntanglementSwappingB.register(KET_VECTOR_FORMALISM)
@EntanglementSwappingB.register(DENSITY_MATRIX_FORMALISM)
class EntanglementSwappingB_Circuit(EntanglementSwappingB):
    """Entanglement swapping protocol for end router.

    The entanglement swapping protocol is an asymmetric protocol.
    EntanglementSwappingB_Circuit should be instantiated on the end nodes, where it waits for swapping results from the middle node.

    Variables:
        EntanglementSwappingB_Circuit.x_cir (Circuit): circuit that corrects state with an x gate.
        EntanglementSwappingB_Circuit.z_cir (Circuit): circuit that corrects state with z gate.
        EntanglementSwappingB_Circuit.x_z_cir (Circuit): circuit that corrects state with an x and z gate.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): name of protocol instance.
        memory (Memory): memory to swap.
        remote_protocol_name (str): name of another protocol to communicate with for swapping.
        remote_node_name (str): name of node hosting the other protocol.
    """

    x_cir = Circuit(1)
    x_cir.x(0)

    z_cir = Circuit(1)
    z_cir.z(0)

    x_z_cir = Circuit(1)
    x_z_cir.x(0)
    x_z_cir.z(0)

    def __init__(self, owner: "Node", name: str, hold_memo: "Memory"):
        """Constructor for entanglement swapping B protocol.

        Args:
            owner (Node): node protocol instance is attached to.
            name (str): name of protocol instance.
            hold_memo (Memory): memory entangled with a memory on middle node.
        """
        super().__init__(owner, name, hold_memo)

    def received_message(self, src: str, msg: "EntanglementSwappingMessage") -> None:
        """Method to receive messages from EntanglementSwappingA.

        Args:
            src (str): name of node sending message.
            msg (EntanglementSwappingMessage): message sent.

        Side Effects:
            Will invoke `update_resource_manager` method.
        """

        log.logger.debug(self.owner.name + f" protocol received_message from node {src}, fidelity={msg.fidelity}")

        assert src == self.remote_node_name

        if msg.fidelity > 0 and self.owner.timeline.now() < msg.expire_time:
            if msg.meas_res == [1, 0]:
                self.owner.timeline.quantum_manager.run_circuit(self.z_cir, [self.memory.qstate_key])
            elif msg.meas_res == [0, 1]:
                self.owner.timeline.quantum_manager.run_circuit(self.x_cir, [self.memory.qstate_key])
            elif msg.meas_res == [1, 1]:
                self.owner.timeline.quantum_manager.run_circuit(self.x_z_cir, [self.memory.qstate_key])

            self.memory.fidelity = msg.fidelity
            self.memory.entangled_memory["node_id"] = msg.remote_node
            self.memory.entangled_memory["memo_id"] = msg.remote_memo
            self.memory.update_expire_time(msg.expire_time)
            self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)
        else:
            self.update_resource_manager(self.memory, MemoryInfo.RAW)
