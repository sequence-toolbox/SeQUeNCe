"""Code for BBPSSW entanglement purification.

This module defines code to support the BBPSSW protocol for entanglement purification.
Success results are pre-determined based on network parameters.
Also defined is the message type used by the BBPSSW code.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node

from ...constants import BELL_DIAGONAL_STATE_FORMALISM
from ...utils import log, metrics
from ...utils.metrics.event_types import EventTypes
from .purification_protocol import PurificationProtocol, BBPSSWMessage, BBPSSWMsgType


@PurificationProtocol.register(BELL_DIAGONAL_STATE_FORMALISM)
class BBPSSW_BDS(PurificationProtocol):
    """Purification protocol instance.

    This class provides an implementation of the BBPSSW purification protocol.
    It should be instantiated on a quantum router node.
    This version of the BBPSSW uses the Bell Diagonal State formalism

    Attributes:
        owner (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        kept_memo: memory to be purified by the protocol (should already be entangled).
        meas_memo: memory to measure and discart (should already be entangled).
        meas_res (int): measurement result from circuit.
        remote_node_name (str): name of other node.
        remote_protocol_name (str): name of other protocol.
        remote_memories (list[str]): name of remote memories.
    """

    def __init__(self, owner: Node, name: str, kept_memo: Memory, meas_memo: Memory):
        """Constructor for purification protocol.

        args:
            owner (Node): Node the protocol of which the protocol is attached.
            name (str): Name of protocol instance.
            kept_memo (Memory): Memory to keep and improve the fidelity.
            meas_memo (Memory): Memory to measure and discard.
        """
        super().__init__(owner, name, kept_memo, meas_memo)

        self.ep_matched = False
        self.protocol_type = 'bbpssw_bds'

    def start(self) -> None:
        """Method to start entanglement purification.

        Run the circuit below on two pairs of entangled memories on both sides of protocol. (Original implementation)

        1) Invoke single-memory decoherence channels, i.e., bds_decohere(), on each involved quantum memory (in total 4)
        purification will use the updated BDS as input. The bds_decohere() method will also update the last_update_time 
        of quantum memories. In this case it will be the time when purification is initiated, thus allowing correct 
        accounting of idling decoherence

        2) Update the BDS with purification_res()
        
        3) Use following trick to determine if the measurement results on both sides equal:
           We consider that both sides do a biased coin flip,
           with head (getting 1) probability p, and tail (getting 0) probability 1-p.
           If we assume that when both sides have 1 or 0 the event corresponds to a successful purification,
           to simulate a correct success probability we require p^2 + (1-p)^2 = q,
           where q is the real success probability of purification.
           As we have proved that the success probability is above 1/2 (for both states with fidelity >= 1/2),
           both solutions to the equation, i.e. p = (1 \pm \sqrt{2q-1})/2, are valid (between 0 and 1);
           We choose p = (1 + \sqrt{2q-1})/2

        Side Effects:
            May update parameters of kept memory.
            Will send message to other protocol instance.
        """
        super().start()
        # get remote memories
        remote_memos = [self.owner.timeline.get_entity_by_name(memo) for memo in self.remote_memories]
        remote_kept_memo: Memory = remote_memos[0]
        remote_meas_memo: Memory = remote_memos[1]

        # Invoke single-memory decoherence channels
        self.meas_memo.bds_decohere()
        remote_meas_memo.bds_decohere()
        self.kept_memo.bds_decohere()
        remote_kept_memo.bds_decohere()

        # calculate correct success probability (q).
        # Also determine BDS density matrix elements of kept entangled pair conditioned on successful purification,
        # immediately after start of purification
        p_success, new_bds = self.purification_res()
        assert 1. >= p_success >= 0.5, 'Entanglement purification success probability should be higher than 1/2.'
        p_1 = (1 + np.sqrt(2 * p_success - 1)) / 2
        if self.owner.get_generator().random() <= p_1:
            self.meas_res = 1
        else:
            self.meas_res = 0

        # modify entangled state of kept pair
        if self.owner.name > self.remote_node_name:  # avoid both ends setting memory state
            keys = [self.kept_memo.qstate_key, remote_kept_memo.qstate_key]
            self.owner.timeline.quantum_manager.set(keys, new_bds)

        log.logger.debug(f'Starting BBPSSW from {self.owner} to {self.remote_node_name}')
        message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES, self.remote_protocol_name, 
                                meas_res=self.meas_res, protocol_type=self.protocol_type)
        self.owner.send_message(self.remote_node_name, message)

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        """Method to receive messages.

        args:
            src (str): name of node that sent the message.
            msg (BBPSSW message): message received.

        Side Effects:
            Will call `update_resource_manager` method.
        """
        if msg.msg_type == BBPSSWMsgType.PURIFICATION_RES:
            purification_success = (self.meas_res == msg.meas_res)
            log.logger.info(self.owner.name + f'received result message, succeeded={purification_success}')
            assert src == self.remote_node_name

            self.update_resource_manager(self.meas_memo, "RAW")

            if purification_success:
                log.logger.info(f'Purification success, measurement results: {self.meas_res}, {msg.meas_res}')
                remote_kept_memory_name = self.remote_memories[0]
                remote_kept_memory: Memory = self.owner.timeline.get_entity_by_name(remote_kept_memory_name)
                remote_kept_memory.bds_decohere()
                self.kept_memo.bds_decohere()
                self.kept_memo.fidelity = self.kept_memo.get_bds_fidelity()
                metrics.record(EventTypes.EP_SUCCESS, self.owner.name, 
                               remote_node=self.remote_node_name, fidelity=self.kept_memo.fidelity)
                self.update_resource_manager(self.kept_memo, state="PURIFIED")
            else:
                log.logger.info(f'Purification failed because measure results: {self.meas_res}, {msg.meas_res}')
                metrics.record(EventTypes.EP_FAILURE, self.owner.name, remote_node=self.remote_node_name)
                self.update_resource_manager(self.kept_memo, state="RAW")

        else:
            raise Exception(f'{msg.msg_type} unknown')

    def purification_res(self) -> tuple[float, npt.NDArray]:
        """Calculate the success probability and output fidelity for BBPSSW purification.

        This implements Eqs. (8) and (9) from "Entanglement Distribution in Quantum Repeater with
        Purification and Optimized Buffer Time": https://arxiv.org/abs/2305.14573.

        The paper assumes identical hardware at both nodes. Here, p1 and eta1 describe the owner node,
        while p2 and eta2 describe the remote node.

        Returns:
            The purification success probability and the Bell-diagonal state of the retained pair.
        """

        assert (self.owner.timeline.quantum_manager.get_active_formalism()
                == BELL_DIAGONAL_STATE_FORMALISM), "Input states should be Bell diagonal states."

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
        assert p1 * p2 > 0, "The uncancelled expression in Eq. (9) requires nonzero gate fidelities."

        # F1 and F2: Phi+ fidelities of the retained and measured input pairs, respectively.
        F1 = kept_input_state.state[0]
        F2 = meas_input_state.state[0]
        # e1 and e2: equal weights of each of the other three Bell states after twirling.
        e1 = (1 - F1) / 3
        e2 = (1 - F2) / 3

        # p_s_w: purification success probability for Werner-state inputs (Eq. 8).
        p_s_w = (
            p1 * p2 * (eta1 * eta2 + (1 - eta1) * (1 - eta2)) * (F1 * F2 + F1 * e2 + e1 * F2 + 5 * e1 * e2)
          + p1 * p2 * (eta1 * (1 - eta2) + (1 - eta1) * eta2) * (2 * F1 * e2 + 2 * e1 * F2 + 4 * e1 * e2)
          + (1 - p1 * p2) / 2 )

        # F_s_w: Phi+ fidelity of the retained pair conditioned on purification success (Eq. 9).
        F_s_w_numerator = (
            (eta1 * eta2 + (1 - eta1) * (1 - eta2)) * (F1 * F2 + e1 * e2)
          + (eta1 * (1 - eta2) + (1 - eta1) * eta2) * (F1 * e2 + e1 * e2)
          + (1 - p1 * p2) / (8 * p1 * p2) )
        
        F_s_w = F_s_w_numerator / (p_s_w / (p1 * p2))

        bds_elems = np.array([F_s_w, (1 - F_s_w) / 3, (1 - F_s_w) / 3, (1 - F_s_w) / 3])
        log.logger.debug(f"{self.name}, before: f={F1:.6f}, {F2:.6f}; after: f={F_s_w:.6f}")

        return p_s_w, bds_elems
