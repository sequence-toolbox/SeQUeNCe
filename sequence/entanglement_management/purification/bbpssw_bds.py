"""Code for BBPSSW entanglement purification.

This module defines code to support the BBPSSW protocol for entanglement purification.
Success results are pre-determined based on network parameters.
Also defined is the message type used by the BBPSSW code.
"""

from typing import List, Tuple
from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node

from ...constants import BELL_DIAGONAL_STATE_FORMALISM
from ...utils import log
from .bbpssw_protocol import BBPSSWProtocol, BBPSSWMessage, BBPSSWMsgType

@BBPSSWProtocol.register(BELL_DIAGONAL_STATE_FORMALISM)
class BBPSSW_BDS(BBPSSWProtocol):
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
        remote_memories (List[str]): name of remote memories.
        is_twirled (bool): whether we twirl the input and output BDS. True: BBPSSW, False: DEJMPS. (default True)
    """

    def __init__(self, owner: "Node", name: str, kept_memo: "Memory", meas_memo: "Memory", is_twirled=True):
        """Constructor for purification protocol.

        args:
            owner (Node): Node the protocol of which the protocol is attached.
            name (str): Name of protocol instance.
            kept_memo (Memory): Memory to keep and improve the fidelity.
            meas_memo (Memory): Memory to measure and discard.
            is_twirled (bool): Whether we twirl the input and output BDS. True: BBPSSW, False: DEJMPS. (default True)
        """
        super().__init__(owner, name, kept_memo, meas_memo)

        self.is_twirled = is_twirled
        self.ep_matched = False

    def start(self) -> None:
        """Method to start entanglement purification.

        Run the circuit below on two pairs of entangled memories on both sides of protocol. (Original implementation)

        Side Effects:
            May update parameters of kept memory.
            Will send message to other protocol instance.
        """
        super().start()
        # get remote memories
        remote_memos = [self.owner.timeline.get_entity_by_name(memo) for memo in self.remote_memories]
        remote_kept_memo: Memory = remote_memos[0]
        remote_meas_memo: Memory = remote_memos[1]

        # first invoke single-memory decoherence channels on each involved quantum memory (in total 4)
        # purification will use the updated BDS as input, and also update the BDS with purification_res
        # the bds_decohere() method will also update the last_update_time of quantum memories
        # in this case it will be the time when purification is initiated, thus allowing correct accounting of idling decoherence

        self.meas_memo.bds_decohere()
        remote_meas_memo.bds_decohere()
        self.kept_memo.bds_decohere()
        remote_kept_memo.bds_decohere()

        # use following trick to determine if the measurement results on both sides equal:
        # We consider that both sides do a biased coin flip,
        # with head (getting 1) probability p, and tail (getting 0) probability 1-p.
        # If we assume that when both sides have 1 or 0 the event corresponds to a successful purification,
        # to simulate a correct success probability we require p^2 + (1-p)^2 = q,
        # where q is the real success probability of purification.
        # As we have proved that the success probability is above 1/2 (for both states with fidelity >= 1/2),
        # both solutions to the equation, i.e. p = (1 \pm \sqrt{2q-1})/2, are valid (between 0 and 1);
        # We choose p = (1 + \sqrt{2q-1})/2

        # calculate correct success probability (q).
        # Also determine BDS density matrix elements of kept entangled pair conditioned on successful purification,
        # immediately after start of purification
        p_success, new_bds = self.purification_res()
        assert 1. >= p_success >= 0.5, \
            'Entanglement purification success probability should be higher than 1/2.'
        p_1 = (1 + np.sqrt(2 * p_success - 1)) / 2
        if self.owner.get_generator().random() <= p_1:
            self.meas_res = 1
        else:
            self.meas_res = 0

        # TODO: the entangle_time attribute of MemoryInfo should be the time when the purification is started,
        #  not the time when purification result is determined (after CC)

        # modify entangled state of kept pair
        if self.owner.name > self.remote_node_name:  # avoid both ends setting memory state
            keys = [self.kept_memo.qstate_key, remote_kept_memo.qstate_key]
            self.owner.timeline.quantum_manager.set(keys, new_bds)

        message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES, self.remote_protocol_name, meas_res=self.meas_res)
        self.owner.send_message(self.remote_node_name, message)

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        """Method to receive messages.

        args:
            src (str): name of node that sent the message.
            msg (BBPSSW message): message received.

        Side Effects:
            Will call `update_resource_manager` method.
        """

        # check the status of entanglement
        if self.meas_memo.entangled_memory['node_id'] is None or self.kept_memo.entangled_memory['node_id'] is None:
            log.logger.info(f'No entanglement for {self.meas_memo} or {self.kept_memo}.')
            # when the AC Protocol expires, the purification protocol on the primary node will get removed, but the purification protocol on the non-primary node is still there
            self.owner.protocols.remove(self)
            return

        if msg.msg_type == BBPSSWMsgType.PURIFICATION_RES:

            purification_success = (self.meas_res == msg.meas_res)
            log.logger.info(self.owner.name + " received result message, succeeded={}".format(purification_success))
            assert src == self.remote_node_name

            self.update_resource_manager(self.meas_memo, "RAW")

            if purification_success:
                log.logger.info(f'Purification success, measurement results: {self.meas_res}, {msg.meas_res}')
                remote_kept_memory_name = self.remote_memories[0]
                remote_kept_memory: Memory = self.owner.timeline.get_entity_by_name(remote_kept_memory_name)
                remote_kept_memory.bds_decohere()
                self.kept_memo.bds_decohere()
                self.kept_memo.fidelity = self.kept_memo.get_bds_fidelity()
                self.update_resource_manager(self.kept_memo, state="ENTANGLED")
            else:
                log.logger.info(f'Purification failed because measure results: {self.meas_res}, {msg.meas_res}')
                self.update_resource_manager(self.kept_memo, state="RAW")

        else:
            raise Exception(f'{msg.msg_type} unknown')

    def purification_res(self) -> Tuple[float, np.array]:
        """Method to calculate the correct success probabilty of a purification trial with BDS input.

        The four BDS density matrix elements of kept entangled pair conditioned on successful purification.

        Returns:
            Tuple[float, np.array]: success probability and BDS density matrix elements of kept entangled pair.
        """

        assert self.owner.timeline.quantum_manager.get_active_formalism() == BELL_DIAGONAL_STATE_FORMALISM, \
            "Input states should be Bell diagonal states."

        kept_input_state = self.owner.timeline.quantum_manager.get(self.kept_memo.qstate_key)
        meas_input_state = self.owner.timeline.quantum_manager.get(self.meas_memo.qstate_key)

        own_node, remote_node = self.owner, self.owner.timeline.get_entity_by_name(self.remote_node_name)

        # gate and measurement fidelities on protocol owner node
        own_node_gate_fid, own_node_meas_fid = own_node.gate_fid, own_node.meas_fid
        # gate and measurement fidelities on remote node
        remote_node_gate_fid, remote_node_meas_fid = remote_node.gate_fid, remote_node.meas_fid

        if self.is_twirled:
            kept_elem_1, kept_elem_2, kept_elem_3, kept_elem_4 = kept_input_state.state[0], (1 - kept_input_state.state[
                0]) / 3, (1 - kept_input_state.state[0]) / 3, (1 - kept_input_state.state[
                0]) / 3  # Diagonal elements of kept pair (twirled)
            meas_elem_1, meas_elem_2, meas_elem_3, meas_elem_4 = meas_input_state.state[0], (1 - meas_input_state.state[
                0]) / 3, (1 - meas_input_state.state[0]) / 3, (1 - meas_input_state.state[
                0]) / 3  # Diagonal elements of measured pair (twirled)
        else:
            kept_elem_1, kept_elem_2, kept_elem_3, kept_elem_4 = kept_input_state.state  # Diagonal elements of kept pair
            meas_elem_1, meas_elem_2, meas_elem_3, meas_elem_4 = meas_input_state.state  # Diagonal elements of measured pair

        # assert 1. >= kept_elem_1 >= 0.5 and 1. >= meas_elem_1 >= 0.5, "Input states should have fidelity above 1/2."
        a, b = (kept_elem_1 + kept_elem_2), (meas_elem_1 + meas_elem_2)

        # calculate success probability with analytical formula
        p_succ = 1 / 2 \
                 + own_node_gate_fid * remote_node_gate_fid \
                 * (own_node_meas_fid * (1 - remote_node_meas_fid) + (1 - own_node_meas_fid) * remote_node_meas_fid) \
                 + own_node_gate_fid * remote_node_gate_fid * (a * b + (1 - a) * (1 - b)) \
                 * (own_node_meas_fid * remote_node_meas_fid + (1 - own_node_meas_fid) * (1 - remote_node_meas_fid)
                    - own_node_meas_fid * (1 - remote_node_meas_fid) - (1 - own_node_meas_fid) * remote_node_meas_fid) \
                 - own_node_gate_fid * remote_node_gate_fid / 2

        # calculate the BDS elements
        new_elem_1 = own_node_gate_fid * remote_node_gate_fid \
                     * ((own_node_meas_fid * remote_node_meas_fid + (1 - own_node_meas_fid) * (
                1 - remote_node_meas_fid)) * (kept_elem_1 * meas_elem_1 + kept_elem_2 * meas_elem_2)
                        + (own_node_meas_fid * (1 - remote_node_meas_fid) + (
                        1 - own_node_meas_fid) * remote_node_meas_fid) * (
                                kept_elem_1 * meas_elem_3 + kept_elem_2 * meas_elem_4)) \
                     + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        new_elem_2 = own_node_gate_fid * remote_node_gate_fid \
                     * ((own_node_meas_fid * remote_node_meas_fid + (1 - own_node_meas_fid) * (
                1 - remote_node_meas_fid)) * (kept_elem_1 * meas_elem_2 + kept_elem_2 * meas_elem_1)
                        + (own_node_meas_fid * (1 - remote_node_meas_fid) + (
                        1 - own_node_meas_fid) * remote_node_meas_fid) * (
                                kept_elem_1 * meas_elem_4 + kept_elem_2 * meas_elem_3)) \
                     + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        new_elem_3 = own_node_gate_fid * remote_node_gate_fid \
                     * ((own_node_meas_fid * remote_node_meas_fid + (1 - own_node_meas_fid) * (
                1 - remote_node_meas_fid)) * (kept_elem_3 * meas_elem_3 + kept_elem_4 * meas_elem_4)
                        + (own_node_meas_fid * (1 - remote_node_meas_fid) + (
                        1 - own_node_meas_fid) * remote_node_meas_fid) * (
                                kept_elem_3 * meas_elem_1 + kept_elem_4 * meas_elem_2)) \
                     + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        new_elem_4 = own_node_gate_fid * remote_node_gate_fid \
                     * ((own_node_meas_fid * remote_node_meas_fid + (1 - own_node_meas_fid) * (
                1 - remote_node_meas_fid)) * (kept_elem_3 * meas_elem_4 + kept_elem_4 * meas_elem_3)
                        + (own_node_meas_fid * (1 - remote_node_meas_fid) + (
                        1 - own_node_meas_fid) * remote_node_meas_fid) * (
                                kept_elem_3 * meas_elem_2 + kept_elem_4 * meas_elem_1)) \
                     + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        if self.is_twirled:
            new_fid = new_elem_1 / p_succ  # normalization by success probability
            bds_elems = np.array([new_fid, (1 - new_fid) / 3, (1 - new_fid) / 3, (1 - new_fid) / 3])
        else:
            bds_elems = np.array([new_elem_1, new_elem_2, new_elem_3, new_elem_4])
            bds_elems = bds_elems / p_succ  # normalization by success probability

        log.logger.debug(
            f"{self.name}, before: f = {kept_elem_1:.6f}, {meas_elem_1:.6f}; after: f = {bds_elems[0]:.6f}")

        return p_succ, bds_elems
