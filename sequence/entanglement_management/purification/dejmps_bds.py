"""Code for DEJMPS entanglement purification with Bell diagonal states."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node

from ...constants import BELL_DIAGONAL_STATE_FORMALISM, DEJMPS
from ...utils import log, metrics
from ...utils.metrics.event_types import EventTypes
from .purification_protocol import PurificationProtocol, BBPSSWMessage, BBPSSWMsgType


@PurificationProtocol.register(DEJMPS)
class DEJMPS_BDS(PurificationProtocol):
    """DEJMPS 2-to-1 purification protocol for Bell diagonal states."""

    def __init__(self, owner: Node, name: str, kept_memo: Memory, meas_memo: Memory):
        """Constructor for the DEJMPS BDS purification protocol.

        Args:
            owner (Node): Node the protocol is attached to.
            name (str): Name of protocol instance.
            kept_memo (Memory): Memory to keep and improve.
            meas_memo (Memory): Memory to measure and discard.
        """
        super().__init__(owner, name, kept_memo, meas_memo)
        self.ep_matched = False
        self.protocol_type = DEJMPS

    def start(self) -> None:
        """Start DEJMPS purification on two Bell-diagonal entangled pairs."""
        super().start()

        remote_memos = [self.owner.timeline.get_entity_by_name(memo) for memo in self.remote_memories]
        remote_kept_memo: Memory = remote_memos[0]
        remote_meas_memo: Memory = remote_memos[1]

        self.meas_memo.bds_decohere()
        remote_meas_memo.bds_decohere()
        self.kept_memo.bds_decohere()
        remote_kept_memo.bds_decohere()

        p_success, new_bds = self.purification_res()
        assert 1 >= p_success >= 0.5, "Entanglement purification success probability should be between 1/2 and 1."
    
        p_1 = (1 + np.sqrt(2 * p_success - 1)) / 2
        self.meas_res = 1 if self.owner.get_generator().random() <= p_1 else 0

        if self.owner.name > self.remote_node_name:
            keys = [self.kept_memo.qstate_key, remote_kept_memo.qstate_key]
            self.owner.timeline.quantum_manager.set(keys, new_bds)

        log.logger.debug(f"Starting DEJMPS from {self.owner} to {self.remote_node_name}")
        message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES, self.remote_protocol_name, 
                                meas_res=self.meas_res, protocol_type=self.protocol_type)
        self.owner.send_message(self.remote_node_name, message)

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        """Receive the remote DEJMPS purification result."""
        if msg.msg_type != BBPSSWMsgType.PURIFICATION_RES:
            raise Exception(f"{msg.msg_type} unknown")

        purification_success = self.meas_res == msg.meas_res
        log.logger.info(self.owner.name + f" received DEJMPS result message, succeeded={purification_success}")
        assert src == self.remote_node_name

        self.update_resource_manager(self.meas_memo, "RAW")

        if purification_success:
            remote_kept_memory_name = self.remote_memories[0]
            remote_kept_memory: Memory = self.owner.timeline.get_entity_by_name(remote_kept_memory_name)
            remote_kept_memory.bds_decohere()
            self.kept_memo.bds_decohere()
            self.kept_memo.fidelity = self.kept_memo.get_bds_fidelity()
            metrics.record(EventTypes.EP_SUCCESS, self.owner.name,
                           remote_node=self.remote_node_name, fidelity=self.kept_memo.fidelity)
            self.update_resource_manager(self.kept_memo, state="PURIFIED")
        else:
            metrics.record(EventTypes.EP_FAILURE, self.owner.name, remote_node=self.remote_node_name)
            self.update_resource_manager(self.kept_memo, state="RAW")

    def purification_res(self) -> tuple[float, npt.NDArray]:
        """Return DEJMPS success probability and successful output BDS.

        SeQUeNCe stores Bell-diagonal coefficients in
        [Phi+, Phi-, Psi+, Psi-] order.  The DEJMPS recurrence is expressed in
        [Phi+, Psi-, Psi+, Phi-] order, so inputs are mapped with indices
        [0, 3, 2, 1].  The recurrence expressions below produce SeQUeNCe's
        storage order directly.
        """
        assert self.owner.timeline.quantum_manager.get_active_formalism() == BELL_DIAGONAL_STATE_FORMALISM, (
                "Input states should be Bell diagonal states.")

        kept_input_state = self.owner.timeline.quantum_manager.get(self.kept_memo.qstate_key)
        meas_input_state = self.owner.timeline.quantum_manager.get(self.meas_memo.qstate_key)

        own_node = self.owner
        remote_node = self.owner.timeline.get_entity_by_name(self.remote_node_name)

        # p1 and p2: probabilities that the owner and remote nodes implement their local CNOT gates perfectly.
        p1 = own_node.gate_fid
        p2 = remote_node.gate_fid
        # eta1 and eta2: probabilities that the owner and remote nodes report the correct measurement result.
        eta1 = own_node.meas_fid
        eta2 = remote_node.meas_fid

        kept_elem_1 = kept_input_state.state[0]
        kept_elem_2 = kept_input_state.state[3]
        kept_elem_3 = kept_input_state.state[2]
        kept_elem_4 = kept_input_state.state[1]

        meas_elem_1 = meas_input_state.state[0]
        meas_elem_2 = meas_input_state.state[3]
        meas_elem_3 = meas_input_state.state[2]
        meas_elem_4 = meas_input_state.state[1]

        # a and b: probability masses of the kept and measured pairs in the {Phi+, Psi-}
        # DEJMPS postselection class.
        a = kept_elem_1 + kept_elem_2
        b = meas_elem_1 + meas_elem_2

        # same_report: probability both readouts are correct or both flip, preserving the true parity.
        same_report = eta1 * eta2 + (1 - eta1) * (1 - eta2)
        # opposite_report: probability exactly one readout flips, reversing the true parity.
        opposite_report = eta1 * (1 - eta2) + (1 - eta1) * eta2
        # joint_gate_fid: probability both local CNOT gates are ideal, assuming independent gate errors.
        joint_gate_fid = p1 * p2

        p_succ = (
            1 / 2 + joint_gate_fid * opposite_report + joint_gate_fid * (a * b + (1 - a) * (1 - b))
            * (same_report - opposite_report) - joint_gate_fid / 2 )

        new_elem_1 = (
            joint_gate_fid * (same_report * (kept_elem_1 * meas_elem_1 + kept_elem_2 * meas_elem_2)
          + opposite_report * (kept_elem_1 * meas_elem_3 + kept_elem_2 * meas_elem_4))
          + (1 - joint_gate_fid) / 8 )

        new_elem_2 = (
            joint_gate_fid * (same_report * (kept_elem_1 * meas_elem_2 + kept_elem_2 * meas_elem_1)
          + opposite_report * (kept_elem_1 * meas_elem_4 + kept_elem_2 * meas_elem_3))
          + (1 - joint_gate_fid) / 8 )

        new_elem_3 = (
            joint_gate_fid * (same_report * (kept_elem_3 * meas_elem_3 + kept_elem_4 * meas_elem_4)
          + opposite_report * (kept_elem_3 * meas_elem_1 + kept_elem_4 * meas_elem_2))
          + (1 - joint_gate_fid) / 8 )

        new_elem_4 = (
            joint_gate_fid * (same_report * (kept_elem_3 * meas_elem_4 + kept_elem_4 * meas_elem_3)
          + opposite_report * (kept_elem_3 * meas_elem_2 + kept_elem_4 * meas_elem_1))
          + (1 - joint_gate_fid) / 8 )
        
        bds_elems = np.array([new_elem_1, new_elem_2, new_elem_3, new_elem_4])
        bds_elems = bds_elems / p_succ

        log.logger.debug(f"{self.name}, before: f={kept_elem_1:.6f}, {meas_elem_1:.6f}; after: f={bds_elems[0]:.6f}")

        return p_succ, bds_elems
