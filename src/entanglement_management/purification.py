"""Code for BBPSSW entanglement purification.

This module defines code to support the BBPSSW protocol for entanglement purification.
Success results are pre-determined based on network parameters.
Also defined is the message type used by the BBPSSW code.
"""

from enum import Enum, auto
from typing import List, Tuple, TYPE_CHECKING
from functools import lru_cache
import numpy as np

if TYPE_CHECKING:
    from ..components.memory import Memory
    from ..topology.node import Node

from ..message import Message
from .entanglement_protocol import EntanglementProtocol
from ..utils import log
from ..components.circuit import Circuit
from ..kernel.quantum_manager import BELL_DIAGONAL_STATE_FORMALISM


class BBPSSWMsgType(Enum):
    """Defines possible message types for entanglement purification."""

    PURIFICATION_RES = auto()


class BBPSSWMessage(Message):
    """Message used by entanglement purification protocols.

    This message contains all information passed between purification protocol instances.

    Attributes:
        msg_type (BBPSSWMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
    """

    def __init__(self, msg_type: BBPSSWMsgType, receiver: str, **kwargs):
        Message.__init__(self, msg_type, receiver)
        if self.msg_type is BBPSSWMsgType.PURIFICATION_RES:
            self.meas_res = kwargs['meas_res']
        else:
            raise Exception("BBPSSW protocol create unknown type of message: %s" % str(msg_type))


class BBPSSW(EntanglementProtocol):
    """Purification protocol instance.

    This class provides an implementation of the BBPSSW purification protocol.
    It should be instantiated on a quantum router node.

    Variables:
        BBPSSW.circuit (Circuit): circuit that purifies entangled memories.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        kept_memo: memory to be purified by the protocol (should already be entangled).
        meas_memo: memory to measure and discart (should already be entangled).
        meas_res (int): measurement result from circuit.
        remote_node_name (str): name of other node.
        remote_protocol_name (str): name of other protocol.
        remote_memories (List[str]): name of remote memories.
        is_bds (bool): whether the formalism of entangled state is Bell diagonal state (default False).
    """

    circuit = Circuit(2)
    circuit.cx(0, 1)
    circuit.measure(1)

    def __init__(self, own: "Node", name: str, kept_memo: "Memory", meas_memo: "Memory", is_bds=False):
        """Constructor for purification protocol.

        Args:
            own (Node): node protocol is attached to.
            name (str): name of protocol instance.
            kept_memo (Memory): memory to have fidelity improved.
            meas_memo (Memory): memory to measure and discard.
            is_bds (bool): whether the formalism of entangled state is Bell diagonal state (default False). 
        """

        assert kept_memo != meas_memo
        EntanglementProtocol.__init__(self, own, name)
        self.memories: List[Memory] = [kept_memo, meas_memo]
        self.kept_memo: Memory = kept_memo
        self.meas_memo: Memory = meas_memo
        self.remote_node_name: str = None
        self.remote_protocol_name: str = None
        self.remote_memories: List[str] = None
        self.meas_res = None
        if self.meas_memo is None:
            self.memories.pop()

        self.is_bds = is_bds

    def is_ready(self) -> bool:
        return self.remote_node_name is not None

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (List[str]): the list of memory names used on other node.
        """
        self.remote_node_name = node
        self.remote_protocol_name = protocol
        self.remote_memories = memories

    def start(self) -> None:
        """Method to start entanglement purification.

        Run the circuit below on two pairs of entangled memories on both sides of protocol. (Original implementation)
        For Bell diagonal state formalism, updated state and success probability are analytically calculated.

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

        log.logger.info(f"{self.own.name} protocol start with partner {self.remote_node_name}")

        assert self.is_ready(), "other protocol is not set; please use set_others function to set it."
        kept_memo_ent = self.kept_memo.entangled_memory["node_id"]
        meas_memo_ent = self.meas_memo.entangled_memory["node_id"]
        assert kept_memo_ent == meas_memo_ent, "mismatch of entangled memories {}, {} on node {}".format(
            kept_memo_ent, meas_memo_ent, self.own.name)
        
        if not self.is_bds:
            assert self.kept_memo.fidelity == self.meas_memo.fidelity > 0.5

            meas_samp = self.own.get_generator().random()
            self.meas_res = self.own.timeline.quantum_manager.run_circuit(
                self.circuit, [self.kept_memo.qstate_key,
                            self.meas_memo.qstate_key],
                meas_samp)
            self.meas_res = self.meas_res[self.meas_memo.qstate_key]

        elif self.is_bds:
            # first invoke single-memory decoherence channels on each involved quantum memory (in total 4)
            # note that bds_decohere() has changed the last_update_time to now, 
            # thus we don't need to change it for the udpated state from purification
            self.meas_memo.bds_decohere()
            self.kept_memo.bds_decohere()
            self.own.timeline.get_entity_by_name(kept_memo_ent).bds_decohere()
            self.own.timeline.get_entity_by_name(meas_memo_ent).bds_decohere()

            # use following trick to determine if the measurement results on both sides equal: 
            # We consider that both sides do a biased coin flip,
            # with head (getting 1) probablity p, and tail (getting 0) probability 1-p.
            # If we assume that when both sides have 1 or 0 the event corresponds to a successful purification,
            # to simulate a correct success probability we require p^2 + (1-p)^2 = q,
            # where q is the real success probability of purification.
            # As we have proved that the success probability is above 1/2 (for both states with fidelity >= 1/2),
            # both solutions to the equation, i.e. p = (1 \pm \sqrt{2q-1})/2, are valid (between 0 and 1);
            # We choose p = (1 + \sqrt{2q-1})/2

            # calculate correct success probabilty (q).
            # Also determine BDS density matrix elements of kept entangled pair conditioned on successful purification,
            # immediately after start of purification
            p_succ, new_bds = self.purification_res()
            assert 1. >= p_succ >= 0.5, \
                "Entanglement purification success probability should be higher than 1/2."
            p_1 = (1 + np.sqrt(2*p_succ - 1)) / 2
            if self.own.get_generator().random() <= p_1:
                self.meas_res = 1
            else:
                self.meas_res = 0

            # TODO: conditioned on success, BDS has been modified since start of purification,
            #  and during classical communication decoherence will happen (if applicable)
            # TODO: the entangle_time attribute of MemoryInfo should be the time when the purification is started,
            #  not the time when purification result is determined (after CC)
            # modify entangled state of kept pair
            # (if failed will be reset automatically, so in advance update does not matter)
            keys = [self.kept_memo.qstate_key, self.own.timeline.get_entity_by_name(kept_memo_ent).qstate_key]

            # avoid both ends setting memory state
            if self.kept_memo.name > kept_memo_ent:
                self.own.timeline.quantum_manager.set(keys, new_bds)

        dst = self.kept_memo.entangled_memory["node_id"]

        message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES,
                                self.remote_protocol_name,
                                meas_res=self.meas_res)
        self.own.send_message(dst, message)

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        """Method to receive messages.

        Args:
            src (str): name of node that sent the message.
            msg (BBPSSW message): message received.

        Side Effects:
            Will call `update_resource_manager` method.
        """

        log.logger.info(
            self.own.name + " received result message, succeeded: {}".format(
                self.meas_res == msg.meas_res))
        assert src == self.remote_node_name

        self.update_resource_manager(self.meas_memo, "RAW")

        if self.meas_res == msg.meas_res:
            if not self.is_bds:
                self.kept_memo.fidelity = BBPSSW.improved_fidelity(self.kept_memo.fidelity)
                self.update_resource_manager(self.kept_memo, state="ENTANGLED")
            elif self.is_bds:
                state = self.own.timeline.quantum_manager.states(self.kept_memo.qstate_key)
                fidelity = state.state[0]
                self.kept_memo.fidelity = fidelity
                # TODO: if time-dependent decoherence exists,
                #  the state should have undergone decoherence during classical communication
                self.update_resource_manager(self.kept_memo, state="ENTANGLED")
        else:
            self.update_resource_manager(self.kept_memo, state="RAW")

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive memory expiration events.

        Args:
            memory (Memory): memory that has expired.

        Side Effects:
            Will call `update_resource_manager` method.
        """

        assert memory in self.memories
        if self.meas_memo is None:
            self.update_resource_manager(memory, "RAW")
        else:
            for memory in self.memories:
                self.update_resource_manager(memory, "RAW")

    def release(self) -> None:
        pass
    
    def purification_res(self) -> Tuple[float, np.array]:
        """Method to calculate the correct success probabilty of a purification trial with BDS input.

        The four BDS density matrix elements of kept entangled pair conditioned on successful purification.

        Returns:
            float: success probability of purification.
            float:
        """

        assert self.own.timeline.quantum_manager.formalism == BELL_DIAGONAL_STATE_FORMALISM, \
            "Input states should be Bell diagonal states."

        kept_input_state = self.own.timeline.quantum_manager.get(self.kept_memo.qstate_key)
        meas_input_state = self.own.timeline.quantum_manager.get(self.meas_memo.qstate_key)

        kept_elem_1, kept_elem_2, kept_elem_3, kept_elem_4 = kept_input_state.state  # Diagonal elements of kept pair
        meas_elem_1, meas_elem_2, meas_elem_3, meas_elem_4 = meas_input_state.state  # Diagonal elements of measured pair
        assert 1. >= kept_elem_1 >= 0.5 and 1. >= meas_elem_1 >= 0.5, "Input states should have fidelity above 1/2."
        a, b = (kept_elem_1 + kept_elem_2), (meas_elem_1, meas_elem_2)  # TODO: how should meas_elem_1 and 2 be combined?

        own_node, remote_node = self.own, self.own.timeline.get_entity_by_name(self.remote_node_name)

        # gate and measurment fidelities on protocol owner node
        own_node_gate_fid, own_node_meas_fid = own_node.gate_fid, own_node.meas_fid
        # gate and measurment fidelities on remote node
        remote_node_gate_fid, remote_node_meas_fid = remote_node.gate_fid, remote_node.meas_fid

        # calculate success probability with analytical formula
        p_succ = 1/2 \
            + own_node_gate_fid * remote_node_gate_fid \
                 * (own_node_meas_fid * (1-remote_node_meas_fid) + (1-own_node_meas_fid) * remote_node_meas_fid) \
            + own_node_gate_fid * remote_node_gate_fid * (a*b + (1-a)*(1-b)) \
                 * (own_node_meas_fid * remote_node_meas_fid + (1-own_node_meas_fid)*(1-remote_node_meas_fid)
                    - own_node_meas_fid * (1-remote_node_meas_fid) - (1-own_node_meas_fid) * remote_node_meas_fid) \
            - own_node_gate_fid * remote_node_gate_fid / 2

        # calculate the BDS elements
        new_elem_1 = own_node_gate_fid * remote_node_gate_fid \
            * ((own_node_meas_fid * remote_node_meas_fid + (1-own_node_meas_fid)*(1-remote_node_meas_fid))*(kept_elem_1*meas_elem_1 + kept_elem_2*meas_elem_2)
                + (own_node_meas_fid * (1-remote_node_meas_fid) + (1-own_node_meas_fid) * remote_node_meas_fid)*(kept_elem_1*meas_elem_3 + kept_elem_2*meas_elem_4)) \
            + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        new_elem_2 = own_node_gate_fid * remote_node_gate_fid \
            * ((own_node_meas_fid * remote_node_meas_fid + (1-own_node_meas_fid)*(1-remote_node_meas_fid))*(kept_elem_1*meas_elem_2 + kept_elem_2*meas_elem_1)
                + (own_node_meas_fid * (1-remote_node_meas_fid) + (1-own_node_meas_fid) * remote_node_meas_fid)*(kept_elem_1*meas_elem_4 + kept_elem_2*meas_elem_3))\
            + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        new_elem_3 = own_node_gate_fid * remote_node_gate_fid \
            * ((own_node_meas_fid * remote_node_meas_fid + (1-own_node_meas_fid)*(1-remote_node_meas_fid))*(kept_elem_3*meas_elem_3 + kept_elem_4*meas_elem_4)
                + (own_node_meas_fid * (1-remote_node_meas_fid) + (1-own_node_meas_fid) * remote_node_meas_fid)*(kept_elem_3*meas_elem_1 + kept_elem_4*meas_elem_2)) \
            + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        new_elem_4 = own_node_gate_fid * remote_node_gate_fid \
            * ((own_node_meas_fid * remote_node_meas_fid + (1-own_node_meas_fid)*(1-remote_node_meas_fid))*(kept_elem_3*meas_elem_4 + kept_elem_4*meas_elem_3)
                + (own_node_meas_fid * (1-remote_node_meas_fid) + (1-own_node_meas_fid) * remote_node_meas_fid)*(kept_elem_3*meas_elem_2 + kept_elem_4*meas_elem_1))\
            + (1 - own_node_gate_fid * remote_node_gate_fid) / 8

        bds_elems = np.array([new_elem_1, new_elem_2, new_elem_3, new_elem_4])
        bds_elems = bds_elems / p_succ  # normalization by success probability
        return p_succ, bds_elems
    
    @staticmethod
    @lru_cache(maxsize=128)
    def improved_fidelity(F: float) -> float:
        """Method to calculate fidelity after purification.
        
        Formula comes from Dur and Briegel (2007) formula (18) page 14.

        Args:
            F (float): fidelity of entanglement.

        Returns:
            float: fidelity of the resultant entangled state assuming successful purification.
        """

        return (F ** 2 + ((1 - F) / 3) ** 2) / (F ** 2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3) ** 2)
