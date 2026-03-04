"""The entanglement swapping protocol for Bell Diagonal State (BDS) formalism.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from .swapping_base import EntanglementSwappingA, EntanglementSwappingB, SwappingMsgType, EntanglementSwappingMessage
from ...utils import log
from ...kernel.quantum_manager import BELL_DIAGONAL_STATE_FORMALISM
from ...resource_management.memory_manager import MemoryInfo

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node


@EntanglementSwappingA.register(BELL_DIAGONAL_STATE_FORMALISM)
class EntanglementSwappingA_BDS(EntanglementSwappingA):
    """Entanglement swapping protocol for middle node/router.

    The entanglement swapping protocol is an asymmetric protocol.
    EntanglementSwappingA should be instantiated on the middle node,
        where it measures a memory from each pair to be swapped.
    Results of measurement and swapping are sent to the end nodes.

    Variables:
        EntanglementSwappingA.circuit (Circuit): circuit that does swapping operations.

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
        is_success (bool): flag to show the result of swapping.
        left_protocol_name (str): name of left protocol.
        right_protocol_name (str): name of right protocol.
        is_twirled (bool): whether the input and output states are twirled into Werner form (default True).
    """

    def __init__(self, owner: Node, name: str, left_memo: Memory, right_memo: Memory, success_prob=1, is_twirled=True):
        """Constructor for entanglement swapping A protocol.

        Args:
            owner (Node): node that protocol instance is attached to.
            name (str): label for swapping protocol instance.
            left_memo (Memory): memory entangled with a memory on one distant node.
            right_memo (Memory): memory entangled with a memory on the other distant node.
            success_prob (float): probability of a successful swapping operation (default 1).
            is_twirled (bool): whether the input and output states are twirled into Werner form (default True).
        """
        assert left_memo != right_memo
        super().__init__(owner, name, left_memo, right_memo, success_prob)
        self.is_twirled = is_twirled

    def start(self) -> None:
        """Method to start entanglement swapping protocol.

        Will run circuit and send measurement results to other protocols.

        Side Effects:
            Will call `update_resource_manager` method.
            Will send messages to other protocols.
        """

        log.logger.info(f"{self.owner.name} middle protocol start with ends {self.left_protocol_name}, {self.right_protocol_name}")

        assert self.left_memo.fidelity > 0 and self.right_memo.fidelity > 0
        assert self.left_memo.entangled_memory["node_id"] == self.left_node
        assert self.right_memo.entangled_memory["node_id"] == self.right_node

        if self.owner.get_generator().random() < self.success_probability():
            log.logger.debug(f'swapping successed!')
            self.is_success = True
            expire_time = min(self.left_memo.get_expire_time(), self.right_memo.get_expire_time())
            # first invoke single-memory decoherence channels on each involved quantum memory (in total 4)
            # note that bds_decohere() has changed the last_update_time to now, 
            # thus we don't need to change it for the udpated state from swapping
            left_remote_memory: Memory = self.owner.timeline.get_entity_by_name(self.left_remote_memo)
            right_remote_memory: Memory = self.owner.timeline.get_entity_by_name(self.right_remote_memo)
            self.left_memo.bds_decohere()
            left_remote_memory.bds_decohere()
            self.right_memo.bds_decohere()
            right_remote_memory.bds_decohere()
            # get BDS conditioned on success, fidelity is the first diagonal element
            new_bds = self.swapping_res()
            fidelity = new_bds[0]
            keys = [left_remote_memory.qstate_key, right_remote_memory.qstate_key]
            self.owner.timeline.quantum_manager.set(keys, new_bds)

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
                                                meas_res=[])
        else:
            log.logger.debug(f'swapping failed!')
            msg_l = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES, self.left_protocol_name, fidelity=0)
            msg_r = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES, self.right_protocol_name, fidelity=0)

        self.owner.send_message(self.left_node, msg_l)
        self.owner.send_message(self.right_node, msg_r)

        self.update_resource_manager(self.left_memo, MemoryInfo.RAW)
        self.update_resource_manager(self.right_memo, MemoryInfo.RAW)

    def swapping_res(self) -> list[float]:
        """Method to calculate the resulting entangled state conditioned on successful swapping, for BDS formalism.

        Returns:
            list[float]: resultant bell diagonal state entries.
        """
        assert self.owner.timeline.quantum_manager.get_active_formalism() == BELL_DIAGONAL_STATE_FORMALISM, (
            "Input states should be Bell diagonal states.")

        left_state = self.owner.timeline.quantum_manager.get(self.left_memo.qstate_key)
        right_state = self.owner.timeline.quantum_manager.get(self.right_memo.qstate_key)

        left_elem_1, left_elem_2, left_elem_3, left_elem_4 = left_state.state  # BDS diagonal elements of left pair
        right_elem_1, right_elem_2, right_elem_3, right_elem_4 = right_state.state  # BDS diagonal elements of right pair

        if self.is_twirled:
            left_elem_2, left_elem_3, left_elem_4 = [(1-left_elem_1)/3] * 3
            right_elem_2, right_elem_3, right_elem_4 = [(1-right_elem_1)/3] * 3

        # assert 1. >= left_elem_1 >= 0.5 and 1. >= right_elem_1 >= 0.5, "Input states should have fidelity above 1/2."
        # gate and measurment fidelities on swapping node, assuming two single-qubit measurements have equal fidelity
        gate_fid, meas_fid = self.owner.gate_fid, self.owner.meas_fid
        # calculate the BDS elements
        c_I = left_elem_1 * right_elem_1 + left_elem_2 * right_elem_2 + left_elem_3 * right_elem_3 + left_elem_4 * right_elem_4
        c_X = left_elem_1 * right_elem_2 + left_elem_2 * right_elem_1 + left_elem_3 * right_elem_4 + left_elem_4 * right_elem_3
        c_Y = left_elem_1 * right_elem_4 + left_elem_4 * right_elem_1 + left_elem_2 * right_elem_3 + left_elem_3 * right_elem_2
        c_Z = left_elem_1 * right_elem_3 + left_elem_3 * right_elem_1 + left_elem_2 * right_elem_4 + left_elem_4 * right_elem_2

        new_elem_1 = gate_fid * (meas_fid**2 * c_I + meas_fid*(1-meas_fid)*(c_X+c_Z) + (1-meas_fid)**2*c_Y) + (1-gate_fid)/4
        new_elem_2 = gate_fid * (meas_fid**2 * c_X + meas_fid*(1-meas_fid)*(c_I+c_Y) + (1-meas_fid)**2*c_Z) + (1-gate_fid)/4
        new_elem_3 = gate_fid * (meas_fid**2 * c_Z + meas_fid*(1-meas_fid)*(c_I+c_Y) + (1-meas_fid)**2*c_X) + (1-gate_fid)/4
        new_elem_4 = gate_fid * (meas_fid**2 * c_Y + meas_fid*(1-meas_fid)*(c_X+c_Z) + (1-meas_fid)**2*c_I) + (1-gate_fid)/4        

        if self.is_twirled:
            bds_elems = [new_elem_1, (1-new_elem_1)/3, (1-new_elem_1)/3, (1-new_elem_1)/3]
        else:
            bds_elems = [new_elem_1, new_elem_2, new_elem_3, new_elem_4]
        
        log.logger.debug(f'before swapping, f = {left_state.state[0]:.6f}, {right_state.state[0]:.6f}; after swapping, f = {bds_elems[0]:.6f}')

        return bds_elems


@EntanglementSwappingB.register(BELL_DIAGONAL_STATE_FORMALISM)
class EntanglementSwappingB_BDS(EntanglementSwappingB):
    """Entanglement swapping protocol for end node/router.

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

    def __init__(self, own: Node, name: str, hold_memo: Memory):
        """Constructor for entanglement swapping B protocol.

        Args:
            owner (Node): node protocol instance is attached to.
            name (str): name of protocol instance.
            hold_memo (Memory): memory entangled with a memory on middle node.
        """
        super().__init__(own, name, hold_memo)

    def received_message(self, src: str, msg: EntanglementSwappingMessage) -> None:
        """Method to receive messages from EntanglementSwappingA.

        Args:
            src (str): name of node sending message.
            msg (EntanglementSwappingMessage): message sent.

        Side Effects:
            Will invoke `update_resource_manager` method.
        """

        log.logger.debug(self.owner.name + " protocol received_message from node {}, fidelity={:.6f}".format(src, msg.fidelity))

        assert src == self.remote_node_name

        if msg.fidelity > 0 and self.owner.timeline.now() < msg.expire_time:
            # if using BDS formalism, updated BDS has been determined analytically taking into account local correction
            self.memory.entangled_memory["node_id"] = msg.remote_node
            self.memory.entangled_memory["memo_id"] = msg.remote_memo
            remote_memory: Memory = self.owner.timeline.get_entity_by_name(msg.remote_memo)
            self.memory.bds_decohere()
            remote_memory.bds_decohere()
            self.memory.fidelity = self.memory.get_bds_fidelity()
            self.memory.update_expire_time(msg.expire_time)
            self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)
        else:
            self.update_resource_manager(self.memory, MemoryInfo.RAW)
