"""Code for entanglement swapping.

This module defines code for entanglement swapping.
Success is pre-determined based on network parameters.
The entanglement swapping protocol is an asymmetric protocol:

* The EntanglementSwappingA instance initiates the protocol and performs the swapping operation.
* The EntanglementSwappingB instance waits for the swapping result from EntanglementSwappingA.

The swapping results decides the following operations of EntanglementSwappingB.
Also defined in this module is the message type used by these protocols.
"""

from enum import Enum, auto
from typing import TYPE_CHECKING, List
from functools import lru_cache

if TYPE_CHECKING:
    from ..components.memory import Memory
    from ..topology.node import Node

from ..message import Message
from .entanglement_protocol import EntanglementProtocol
from ..utils import log
from ..components.circuit import Circuit


class SwappingMsgType(Enum):
    """Defines possible message types for entanglement generation."""

    SWAP_RES = auto()


class EntanglementSwappingMessage(Message):
    """Message used by entanglement swapping protocols.

    This message contains all information passed between swapping protocol instances.

    Attributes:
        msg_type (SwappingMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        fidelity (float): fidelity of the newly swapped memory pair.
        remote_node (str): name of the distant node holding the entangled memory of the new pair.
        remote_memo (int): index of the entangled memory on the remote node.
        expire_time (int): expiration time of the new memory pair.
    """

    def __init__(self, msg_type: SwappingMsgType, receiver: str, **kwargs):
        Message.__init__(self, msg_type, receiver)
        if self.msg_type is SwappingMsgType.SWAP_RES:
            self.fidelity = kwargs.get("fidelity")
            self.remote_node = kwargs.get("remote_node")
            self.remote_memo = kwargs.get("remote_memo")
            self.expire_time = kwargs.get("expire_time")
            self.meas_res = kwargs.get("meas_res")
        else:
            raise Exception("Entanglement swapping protocol create unkown type of message: %s" % str(msg_type))

    def __str__(self):
        if self.msg_type == SwappingMsgType.SWAP_RES:
            return "EntanglementSwappingMessage: msg_type: %s; fidelity: %.2f; remote_node: %s; remote_memo: %s; " % (
                self.msg_type, self.fidelity, self.remote_node, self.remote_memo)


class EntanglementSwappingA(EntanglementProtocol):
    """Entanglement swapping protocol for middle router.

    The entanglement swapping protocol is an asymmetric protocol.
    EntanglementSwappingA should be instantiated on the middle node, where it measures a memory from each pair to be swapped.
    Results of measurement and swapping are sent to the end routers.

    Variables:
        EntanglementSwappingA.circuit (Circuit): circuit that does swapping operations.

    Attributes:
        own (Node): node that protocol instance is attached to.
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

    def __init__(self, own: "Node", name: str, left_memo: "Memory", right_memo: "Memory", success_prob=1,
                 degradation=0.95):
        """Constructor for entanglement swapping A protocol.

        Args:
            own (Node): node that protocol instance is attached to.
            name (str): label for swapping protocol instance.
            left_memo (Memory): memory entangled with a memory on one distant node.
            right_memo (Memory): memory entangled with a memory on the other distant node.
            success_prob (float): probability of a successful swapping operation (default 1).
            degradation (float): degradation factor of memory fidelity after swapping (default 0.95).
        """

        assert left_memo != right_memo
        EntanglementProtocol.__init__(self, own, name)
        self.memories = [left_memo, right_memo]
        self.left_memo = left_memo
        self.right_memo = right_memo
        self.left_node = left_memo.entangled_memory['node_id']
        self.left_remote_memo = left_memo.entangled_memory['memo_id']
        self.right_node = right_memo.entangled_memory['node_id']
        self.right_remote_memo = right_memo.entangled_memory['memo_id']
        self.success_prob = success_prob
        self.degradation = degradation
        self.is_success = False
        self.left_protocol_name = None
        self.right_protocol_name = None

    def is_ready(self) -> bool:
        return self.left_protocol_name is not None \
               and self.right_protocol_name is not None

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (List[str]): the list of memories name used on other node.
        """

        if node == self.left_memo.entangled_memory["node_id"]:
            self.left_protocol_name = protocol
        elif node == self.right_memo.entangled_memory["node_id"]:
            self.right_protocol_name = protocol
        else:
            raise Exception("Cannot pair protocol %s with %s" % (self.name, protocol))

    def start(self) -> None:
        """Method to start entanglement swapping protocol.

        Will run circuit and send measurement results to other protocols.

        Side Effects:
            Will call `update_resource_manager` method.
            Will send messages to other protocols.
        """

        log.logger.info(f"{self.own.name} middle protocol start with ends "
                        f"{self.left_protocol_name}, "
                        f"{self.right_protocol_name}")

        assert self.left_memo.fidelity > 0 and self.right_memo.fidelity > 0
        assert self.left_memo.entangled_memory["node_id"] == self.left_node
        assert self.right_memo.entangled_memory["node_id"] == self.right_node

        if self.own.get_generator().random() < self.success_probability():
            fidelity = self.updated_fidelity(self.left_memo.fidelity, self.right_memo.fidelity)
            self.is_success = True

            expire_time = min(self.left_memo.get_expire_time(), self.right_memo.get_expire_time())

            meas_samp = self.own.get_generator().random()
            meas_res = self.own.timeline.quantum_manager.run_circuit(
                self.circuit, [self.left_memo.qstate_key,
                               self.right_memo.qstate_key], meas_samp)
            meas_res = [meas_res[self.left_memo.qstate_key], meas_res[self.right_memo.qstate_key]]

            msg_l = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES,
                                                self.left_protocol_name,
                                                fidelity=fidelity,
                                                remote_node=self.right_memo.entangled_memory["node_id"],
                                                remote_memo=self.right_memo.entangled_memory["memo_id"],
                                                expire_time=expire_time,
                                                meas_res=[])
            msg_r = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES,
                                                self.right_protocol_name,
                                                fidelity=fidelity,
                                                remote_node=self.left_memo.entangled_memory["node_id"],
                                                remote_memo=self.left_memo.entangled_memory["memo_id"],
                                                expire_time=expire_time,
                                                meas_res=meas_res)
        else:
            msg_l = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES,
                                                self.left_protocol_name,
                                                fidelity=0)
            msg_r = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES,
                                                self.right_protocol_name,
                                                fidelity=0)

        self.own.send_message(self.left_node, msg_l)
        self.own.send_message(self.right_node, msg_r)

        self.update_resource_manager(self.left_memo, "RAW")
        self.update_resource_manager(self.right_memo, "RAW")

    def success_probability(self) -> float:
        """A simple model for BSM success probability."""

        return self.success_prob

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

    def received_message(self, src: str, msg: "Message") -> None:
        """Method to receive messages (should not be used on A protocol)."""

        raise Exception("EntanglementSwappingA protocol '{}' should not receive messages.".format(self.name))

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive memory expiration events.

        Releases held memories on current node.
        Memories at the remote node are released as well.

        Args:
            memory (Memory): memory that expired.

        Side Effects:
            Will invoke `update` method of attached resource manager.
            Will invoke `release_remote_protocol` or `release_remote_memory` method of resource manager.
        """

        assert self.is_ready() is False
        if self.left_protocol_name:
            self.release_remote_protocol(self.left_node)
        else:
            self.release_remote_memory(self.left_node, self.left_remote_memo)
        if self.right_protocol_name:
            self.release_remote_protocol(self.right_node)
        else:
            self.release_remote_memory(self.right_node, self.right_remote_memo)

        for memo in self.memories:
            if memo == memory:
                self.update_resource_manager(memo, "RAW")
            else:
                self.update_resource_manager(memo, "ENTANGLED")

    def release_remote_protocol(self, remote_node: str):
        self.own.resource_manager.release_remote_protocol(remote_node, self)

    def release_remote_memory(self, remote_node: str, remote_memo: str):
        self.own.resource_manager.release_remote_memory(remote_node, remote_memo)


class EntanglementSwappingB(EntanglementProtocol):
    """Entanglement swapping protocol for middle router.

    The entanglement swapping protocol is an asymmetric protocol.
    EntanglementSwappingB should be instantiated on the end nodes, where it waits for swapping results from the middle node.

    Variables:
        EntanglementSwappingB.x_cir (Circuit): circuit that corrects state with an x gate.
        EntanglementSwappingB.z_cir (Circuit): circuit that corrects state with z gate.
        EntanglementSwappingB.x_z_cir (Circuit): circuit that corrects state with an x and z gate.

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

    def __init__(self, own: "Node", name: str, hold_memo: "Memory"):
        """Constructor for entanglement swapping B protocol.

        Args:
            own (Node): node protocol instance is attached to.
            name (str): name of protocol instance.
            hold_memo (Memory): memory entangled with a memory on middle node.
        """

        EntanglementProtocol.__init__(self, own, name)

        self.memories = [hold_memo]
        self.memory = hold_memo
        self.remote_protocol_name = None
        self.remote_node_name = None

    def is_ready(self) -> bool:
        return self.remote_protocol_name is not None

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (List[str]): the list of memory names used on other node.
        """
        self.remote_node_name = node
        self.remote_protocol_name = protocol

    def received_message(self, src: str, msg: "EntanglementSwappingMessage") -> None:
        """Method to receive messages from EntanglementSwappingA.

        Args:
            src (str): name of node sending message.
            msg (EntanglementSwappingMesssage): message sent.

        Side Effects:
            Will invoke `update_resource_manager` method.
        """

        log.logger.debug(
            self.own.name + " protocol received_message from node {}, fidelity={}".format(src, msg.fidelity))

        assert src == self.remote_node_name

        if msg.fidelity > 0 and self.own.timeline.now() < msg.expire_time:
            if msg.meas_res == [1, 0]:
                self.own.timeline.quantum_manager.run_circuit(self.z_cir, [self.memory.qstate_key])
            elif msg.meas_res == [0, 1]:
                self.own.timeline.quantum_manager.run_circuit(self.x_cir, [self.memory.qstate_key])
            elif msg.meas_res == [1, 1]:
                self.own.timeline.quantum_manager.run_circuit(self.x_z_cir, [self.memory.qstate_key])

            self.memory.fidelity = msg.fidelity
            self.memory.entangled_memory["node_id"] = msg.remote_node
            self.memory.entangled_memory["memo_id"] = msg.remote_memo
            self.memory.update_expire_time(msg.expire_time)
            self.update_resource_manager(self.memory, "ENTANGLED")
        else:
            self.update_resource_manager(self.memory, "RAW")

    def start(self) -> None:
        log.logger.info(f"{self.own.name} end protocol start with partner {self.remote_node_name}")

    def memory_expire(self, memory: "Memory") -> None:
        """Method to deal with expired memories.

        Args:
            memory (Memory): memory that expired.

        Side Effects:
            Will update memory in attached resource manager.
        """

        self.update_resource_manager(self.memory, "RAW")

    def release(self) -> None:
        self.update_resource_manager(self.memory, "ENTANGLED")
