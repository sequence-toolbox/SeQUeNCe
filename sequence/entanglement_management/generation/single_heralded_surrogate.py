"""A surrogate for single heralded entanglement generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scipy.stats import geom
from scipy.stats._distn_infrastructure import rv_discrete_frozen

from .generation_base import EntanglementGenerationA, EntanglementGenerationB
from .generation_message import GenerationMsgType
from .single_heralded import SingleHeraldedA, SingleHeraldedB
from ...components.bsm import SingleHeraldedBSM
from ...components.detector import Detector
from ...components.memory import Memory
from ...components.optical_channel import ClassicalChannel, QuantumChannel
from ...constants import SINGLE_HERALDED_SURROGATE
from ...kernel.event import Event
from ...kernel.process import Process
from ...message import Message
from ...utils import log

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline
    from ...topology.node import Node, BSMNode


class SurrogateGenerationMessage(Message):
    """Message used by surrogate entanglement generation protocols.

    Attributes:
        msg_type (GenerationMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        protocol_type (str): identifies the generation protocol.
        time (int): surrogate time (if `msg_type == NEGOTIATE`).
    """

    __slots__ = ["time"]

    def __init__(self, msg_type: GenerationMsgType, receiver: str | None, protocol_type: str, **kwargs):
        super().__init__(msg_type, receiver)
        self.protocol_type = protocol_type
        self.time: int | None = None  # the entanglement succeed time computed from the surrogate

        fields = {GenerationMsgType.NEGOTIATE: ["time"],
                  GenerationMsgType.NEGOTIATE_ACK: []}

        if msg_type in fields:
            for field in fields[msg_type]:
                setattr(self, field, kwargs.get(field))
        else:
            raise ValueError(f"SurrogateGeneration generated invalid message type {msg_type}")

    def __repr__(self):
        match self.msg_type:
            case GenerationMsgType.NEGOTIATE:
                return f"type: {self.msg_type}, time: {self.time}"
            case GenerationMsgType.NEGOTIATE_ACK:
                return f"type: {self.msg_type}"
            case _:
                raise ValueError(f"SurrogateGeneration generated invalid message type {self.msg_type}")


@EntanglementGenerationA.register(SINGLE_HERALDED_SURROGATE)
class SingleHeraldedASurrogate(SingleHeraldedA):
    """
    A surrogate for SingleHeraldedA. It should behave very similarly to the original 
    SingleHeraldedA protocol performance wise, but will skip a lot of the actual physical operations.

    Instance Attributes:
        owner (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
        middle (str): name of the middle BSM node.
        other (str): name of the other end node.
        memory (Memory): memory object used for entanglement generation.
        raw_fidelity (float): the raw fidelity of generated entangled pair.
        raw_epr_errors (list[float]): the raw EPR pair Pauli error rates in X, Y, Z order.
        bsm_res (list[int]): the BSM measurement results from the middle BSM node.
        protocol_type (str): The type of the protocol instance.
        surrogate (tuple[float, rv_discrete_frozen]): (time per attempt, geometric distribution of success attempts)

    Class Attributes:
        memory_efficiency (dict[str, float]): Memory name to its efficiency.
        qchannel_transmission_probability (dict[str, float]): Quantum channel name to its transmission efficiency.
        detector_efficiency (dict[str, float]): Detector name to efficiency.
        bsm_success_rate (dict[str, float]): BSM name to success rate.
        cchannel_delay (dict[str, float]): Classical channel name to its delay.
        surrogates (dict[tuple[str, str], tuple[float, rv_discrete_frozen]]): (primary node, non-primary node) to surrogate.
        
    Note: The class attributes should be set at the beginning of the simulation. 
          If the class attributes are not all set, the surrogate will reduce to the original SingleHeraldedA.
    """
    memory_efficiency: dict[str, float] = None                 # memory name to its efficiency
    qchannel_transmission_probability: dict[str, float] = None # quantum channel name to its transmission efficiency
    detector_efficiency: dict[str, float] = None               # detector name to efficiency
    bsm_success_rate: dict[str, float] = None                  # BSM name to success rate
    cchannel_delay: dict[str, float] = None                    # classical channel name to its delay
    surrogates: dict[tuple[str, str], tuple[float, rv_discrete_frozen]] = {}  # (primary node, non-primary node) to surrogate

    def __init__(self, owner: Node, name: str, middle: str, other: str, memory: Memory,
                 raw_fidelity: float = None, raw_epr_errors: list[float] = None):
        """Initialize the SingleHeraldedASurrogate protocol.
        
        Args:
            owner (Node): The node that owns this protocol instance.
            name (str): The name of the protocol instance.
            middle (str): The middle node in the entanglement generation.
            other (str): The other node in the entanglement generation.
            memory (Memory): The memory used for entanglement generation.
            raw_fidelity (float, optional): The raw fidelity of the entangled state.
            raw_epr_errors (list[float], optional): The raw EPR errors of the entangled state.
        """
        super().__init__(owner, name, middle, other, memory, raw_fidelity, raw_epr_errors)
        self.protocol_type = SINGLE_HERALDED_SURROGATE
        self.surrogate: tuple[float, rv_discrete_frozen] = None

    def get_memory_name(self, protocol_name: str) -> str:
        """Get the memory ID associated with the given protocol instance. 
        Eg. EGA.router_1.MemoryArray[0] -> router_1.MemoryArray[0]
        
        Args:
            protocol_name (str): The name of the protocol instance.

        Returns:
            str: The memory ID associated with the given protocol instance.
        """
        return protocol_name.split('.', 1)[1]
    
    def get_qchannel_name(self, node_name: str, bsm_node_name: str) -> str:
        """Get the quantum channel name between the given node and BSM node.

        Args:
            node_name (str): The name of the node.
            bsm_node_name (str): The name of the BSM node.

        Returns:
            str: The name of the quantum channel.
        """
        return f"qc-{node_name}-{bsm_node_name}"

    def get_detector_name(self, bsm_node_name: str, index: int) -> str:
        """Get the detector name for the given BSM node and index.

        Args:
            bsm_node_name (str): The name of the BSM node.
            index (int): The index of the detector.

        Returns:
            str: The name of the detector.
        """
        return f'{bsm_node_name}.BSM_{index}'

    def get_bsm_name(self, bsm_node_name: str) -> str:
        """Get the BSM name for the given BSM node.

        Args:
            bsm_node_name (str): The name of the BSM node.

        Returns:
            str: The name of the BSM.
        """
        return f'{bsm_node_name}.BSM'

    def get_cchannel_name(self, node_name: str, other_node_name: str) -> str:
        """Get the classical channel name between the given node and other node.

        Args:
            node_name (str): The name of the node.
            other_node_name (str): The name of the other node.

        Returns:
            str: The name of the classical channel.
        """
        return f"cc-{node_name}-{other_node_name}"

    def get_rtt_count(self) -> float:
        """The primary node will call this method and if it appears first in the reservation path, the RTT is 2.5
           Otherwise, the remote node appears first in the reservation path and the RTT is 2

        Returns:
            float: The RTT for a single entanglement generation attempt.
        """
        path = self.rule.reservation.path
        for node in path:
            if node == self.owner.name:
                return 2.5
            elif node == self.remote_node_name:
                return 2
        else:
            raise ValueError("Node not found in the path.")

    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        """Pair this protocol with the remote protocol instance. Sets the primary flag based on node names.
           Also set up the surrogate model.

        Args:
            protocol (str): The name of the remote protocol instance.
            node (str): The name of the remote node.
            memories (list[str]): The list of memory IDs at the remote node.
        """
        super().set_others(protocol, node, memories)
        if self.surrogate_parameter_is_set():
            if self.primary:
                key = (self.owner.name, node)
                if key in self.surrogates:
                    self.surrogate = self.surrogates[key]
                else:
                    # get memory efficiency
                    memory = self.get_memory_name(self.name)
                    memory_other = self.get_memory_name(self.remote_protocol_name)
                    memory_efficiency = self.memory_efficiency[memory]
                    memory_efficiency_other = self.memory_efficiency[memory_other]
                    # get quantum channel transmission probability
                    qchannel = self.get_qchannel_name(self.owner.name, self.middle)
                    qchannel_other = self.get_qchannel_name(self.remote_node_name, self.middle)
                    qchannel_transmission_probability = self.qchannel_transmission_probability[qchannel]
                    qchannel_transmission_probability_other = self.qchannel_transmission_probability[qchannel_other]
                    # get detector efficiency
                    detector1 = self.get_detector_name(self.middle, 0)
                    detector2 = self.get_detector_name(self.middle, 1)
                    detector_efficiency1 = self.detector_efficiency[detector1]
                    detector_efficiency2 = self.detector_efficiency[detector2]
                    # get bsm success rate
                    bsm = self.get_bsm_name(self.middle)
                    bsm_success_rate = self.bsm_success_rate[bsm]
                    # overall success probability per attempt
                    overall_probability = (memory_efficiency * memory_efficiency_other 
                                           * qchannel_transmission_probability * qchannel_transmission_probability_other
                                           * detector_efficiency1 * detector_efficiency2 * bsm_success_rate)
                    # get classical channel delay
                    cchannel = self.get_cchannel_name(self.owner.name, self.remote_node_name)
                    cchannel_delay = self.cchannel_delay[cchannel]
                    # get time per entanglement generation attempt
                    rtt_time = 2 * cchannel_delay
                    rtt_count = self.get_rtt_count()
                    time_per_attempt = rtt_count * rtt_time
                    # finally get the expected time for successful entanglement generation
                    expected_time = time_per_attempt / overall_probability
                    # store the expected time for this surrogate
                    self.surrogates[key] = (time_per_attempt, geom(overall_probability))
                    self.surrogate = self.surrogates[key]
                    log.logger.info(f"Surrogate key: {key}, Overall probability: {overall_probability}, "
                                       f"Time per attempt: {time_per_attempt}, Expected time: {expected_time}")

    @classmethod
    def set_surrogate_parameter_from_timeline(cls, timeline: Timeline) -> None:
        """Set the surrogate parameters from the timeline.

        Args:
            timeline (Timeline): The simulation timeline containing the entities.
        """
        cchannel_delay = {}
        memory_efficiency = {}
        qchannel_transmission_probability = {}
        detector_efficiency = {}
        bsm_success_rate = {}

        for name, entity in timeline.entities.items():
            if isinstance(entity, ClassicalChannel):
                cchannel_delay[name] = entity.delay
            elif isinstance(entity, Memory):
                memory_efficiency[name] = entity.efficiency
            elif isinstance(entity, QuantumChannel):
                qchannel_transmission_probability[name] = 1 - entity.loss
            elif isinstance(entity, Detector):
                detector_efficiency[name] = entity.efficiency
            elif isinstance(entity, SingleHeraldedBSM):
                bsm_success_rate[name] = entity.success_rate

        cls.memory_efficiency = memory_efficiency
        cls.qchannel_transmission_probability = qchannel_transmission_probability
        cls.detector_efficiency = detector_efficiency
        cls.bsm_success_rate = bsm_success_rate
        cls.cchannel_delay = cchannel_delay

    def surrogate_parameter_is_set(self) -> bool:
        """Check if the surrogate parameters are all set.

        Return:
            True if all surrogate parameters are set, False otherwise.
        """
        if (self.cchannel_delay and self.memory_efficiency and self.qchannel_transmission_probability 
                and self.detector_efficiency and self.bsm_success_rate):
            return True
        return False

    def start(self) -> None:
        """Method to start "one round" in the entanglement generation protocol (there are two rounds in Barrett-Kok).

        Will start negotiations with other protocol (if primary).

        Side Effects:
            Will send message through attached node.
        """
        if self.surrogate_parameter_is_set():
            if self not in self.owner.protocols:
                return
            text = f"{self.owner.name} {self.name} surrogate protocol start with partner {self.remote_protocol_name}"
            log.logger.info(text)

            if self.primary:
                time_per_attempt, geom_distribution = self.surrogate
                number_of_attempts = geom_distribution.rvs()
                entanglement_total_time = round(time_per_attempt * number_of_attempts)
                log.logger.info(f"{self.owner.name} {self.name} surrogate: number of attempts: {number_of_attempts},"
                                   f" time per attempt: {time_per_attempt}, total time: {entanglement_total_time}")
                cchannel = self.get_cchannel_name(self.owner.name, self.remote_node_name)
                cchannel_delay = self.cchannel_delay[cchannel]
                time_before_start = round(cchannel_delay if self.get_rtt_count() == 2 else 2 * cchannel_delay)
                entanglement_succeed_time = self.owner.timeline.now() - time_before_start + entanglement_total_time
                process = Process(self, "entanglement_succeed", [])
                event = Event(entanglement_succeed_time, process)
                self.owner.timeline.schedule(event)
                self.scheduled_events.append(event)

                # send message
                message = SurrogateGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name,
                                                     self.protocol_type, time=entanglement_succeed_time)
                self.owner.send_message(self.remote_node_name, message)

        else:
            super().start()

    def received_message(self, src: str, message: SurrogateGenerationMessage) -> None:
        """Handle received messages for the surrogate protocol.

        Args:
            src (str): The source node name.
            message (SurrogateGenerationMessage): The received message.
        """
        if self.surrogate_parameter_is_set():
            if message.msg_type == GenerationMsgType.NEGOTIATE: # non-primary receives NEGOTIATE message from primary
                # Handle negotiation message
                log.logger.info(f"{self.owner.name} {self.name} received NEGOTIATE message from {src} at time {message.time}")
                entanglement_succeed_time = message.time
                process = Process(self, "entanglement_succeed", [])
                event = Event(entanglement_succeed_time, process)
                self.owner.timeline.schedule(event)
                self.scheduled_events.append(event)
                message = SurrogateGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name,
                                                    self.protocol_type)
                self.owner.send_message(src, message)

            elif message.msg_type == GenerationMsgType.NEGOTIATE_ACK: # primary receives ACK message from non-primary
                log.logger.info(f"{self.owner.name} {self.name} received NEGOTIATE_ACK message from {src}")
                # do nothing
        else:
            super().received_message(src, message)

    def entanglement_succeed(self) -> None:
        """Handle the entanglement succeed event.
        """
        log.logger.info(f"{self.owner.name} {self.name} surrogate: entanglement succeed at {self.owner.timeline.now()}")
        quantum_manager = self.owner.timeline.quantum_manager
        self_key = self._qstate_key
        remote_memory: Memory = self.owner.timeline.get_entity_by_name(self.remote_memo_id)
        remote_key = remote_memory.qstate_key
        keys = [self_key, remote_key]
        if self_key not in quantum_manager.states:
            in_fidelity = 1 - self.raw_fidelity
            x_elem, y_elem, z_elem = (error * in_fidelity for error in self.raw_epr_errors)
            state = [self.raw_fidelity, z_elem, x_elem, y_elem]
            quantum_manager.set(keys, state)
            # decoherence not done yet
        self._entanglement_succeed()


@EntanglementGenerationB.register(SINGLE_HERALDED_SURROGATE)
class SingleHeraldedBSurrogate(SingleHeraldedB):
    """
    A surrogate for SingleHeraldedB
    """
    def __init__(self, owner: BSMNode, name: str, others: list[str]):
        super().__init__(owner, name, others)
        self.protocol_type = SINGLE_HERALDED_SURROGATE
