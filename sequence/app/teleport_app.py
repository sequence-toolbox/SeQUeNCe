""" TeleportApp Module
This module implements the TeleportApp class, which is responsible for managing quantum teleportation
between quantum nodes. It utilizes the TeleportProtocol to handle the teleportation process,
including the reservation of entangled pairs and the application of corrections based on classical messages.
"""

from .request_app import RequestApp
from ..utils import log
from ..entanglement_management.teleportation import TeleportMsgType, TeleportProtocol, TeleportMessage
from ..topology.node import DQCNode
from ..resource_management.memory_manager import MemoryInfo
from ..kernel.process import Process
from ..kernel.event import Event


class TeleportApp(RequestApp):
    """Code for the teleport application.

    TeleportApp is a specialized RequestApp that implements quantum teleportation.
    It handles the teleportation protocol between two quantum nodes (Alice and Bob).

    Attributes:
        node (DQCNode): The quantum node this app is attached to.
        name (str): The name of the teleport application.
        results (list): A list of results of (timestamp, teleported_state)
        teleport_protocols (list[TeleportProtocol]): A list of teleportation protocol instances.
    """
    def __init__(self, node: DQCNode):
        super().__init__(node)
        self.name = f"{self.node.name}.TeleportApp"
        node.teleport_app = self   # register ourselves so incoming TeleportMessage lands here:
        self.results = []          # where we’ll collect Bob’s teleported state
        self.teleport_protocols: list[TeleportProtocol] = [] # a list of teleport protocol instances
        log.logger.debug(f"{self.name}: initialized")

    def start(self, responder: str, start_t: int, end_t: int, memory_size: int, fidelity: float, data_memory_index: int):
        """Start the teleportation process.

        NOTE: only teleport one data memory qubit

        Args: 
            responder (str): Name of the responder node (Bob).
            start_t (int): Start time of the teleportation (in ps).
            end_t (int): End time of the teleportation (in ps).
            memory_size (int): Size of the memory used for the teleportation.
            fidelity (float): Target fidelity of the teleportation.
            data_memory_index (int): Index of the data qubit to be teleported.
        """
        log.logger.debug(f"{self.name}: start() → responder={responder}, data_memory_index={data_memory_index}")

        # reserve and generate EPR pair
        super().start(responder, start_t, end_t, memory_size, fidelity)

        # init a new teleportation protocol for Alice only, and append to the list
        teleport_protocol = TeleportProtocol(self.node, alice=True, data_memory_index=data_memory_index, remote_node_name=responder)
        self.teleport_protocols.append(teleport_protocol)


    def get_reservation_result(self, reservation, result: bool):
        """Handle the reservation result from the network manager.

        Args:
            reservation (Reservation): The reservation object.
            result (bool): True if the reservation was successful, False otherwise.
        """
        super().get_reservation_result(reservation, result)
        log.logger.debug(f"{self.name}: reservation_result → {result}")

    def get_memory(self, info: MemoryInfo):
        """Handle memory state changes.

        Args:
            info (MemoryInfo): Information about the memory state change.
        """
        log.logger.debug(f"{self.name}: get_memory, name={info.memory.name}, state={info.state}")
        # once we see our entangled half, hand it to the protocol
        if info.index in self.memo_to_reservation:
            if info.state == "ENTANGLED":
                for teleport_protocol in self.teleport_protocols:
                    this_node = info.memory.owner.name
                    remote_node = info.remote_node
                    if this_node == teleport_protocol.owner.name and remote_node == teleport_protocol.remote_node_name:
                        # this node is Alice
                        teleport_protocol.set_alice_comm_memory_name(info.memory.name)
                        teleport_protocol.set_alice_comm_memory(info.memory)
                        teleport_protocol.set_bob_comm_memory_name(info.remote_memo)
                        reservation = self.memo_to_reservation[info.index]
                        # Let Bob first execute EntanglementGenerationA._entanglement_succeed(), then let Alice do the Bell measurement
                        time_now = self.node.timeline.now()
                        process = Process(teleport_protocol, 'alice_bell_measurement', [reservation])
                        priority = self.node.timeline.schedule_counter
                        event = Event(time_now, process, priority)
                        self.node.timeline.schedule(event)
                        break # if no matching protocol found, go to else clause
                else:
                    # this node is Bob, create the new teleport protocol instance, then append to self.teleport_protocols
                    teleport_protocol = TeleportProtocol(self.node, alice=False, remote_node_name=info.remote_node)
                    teleport_protocol.set_bob_comm_memory_name(info.memory.name)
                    teleport_protocol.set_bob_comm_memory(info.memory)
                    teleport_protocol.set_alice_comm_memory_name(info.remote_memo)
                    self.teleport_protocols.append(teleport_protocol)

    def received_message(self, src: str, msg: TeleportMessage):
        """Handle incoming teleport messages.

        Args:
            src (str): Source node name.
            msg (TeleportMessage): The teleport message received.
        """
        log.logger.debug(f"{self.name} received_message from {src}: {msg}")
        if msg.msg_type is TeleportMsgType.MEASUREMENT_RESULT:  # Bob receives measurement result from Alice
            for teleport_protocol in self.teleport_protocols:   # find the correct teleport protocol on Bob's side
                if src == teleport_protocol.remote_node_name and msg.bob_comm_memory_name == teleport_protocol.bob_comm_memory_name:
                    teleport_protocol.received_message(src, msg)
                    self.node.resource_manager.expire_rules_by_reservation(msg.reservation)                    # early release of resources
                    self.node.resource_manager.update(None, teleport_protocol.bob_comm_memory, MemoryInfo.RAW) # release the bob comm memory
                    teleport_protocol.bob_acknowledge_complete(msg.reservation)
                    self.teleport_protocols.remove(teleport_protocol)  # remove the protocol instance, it's lifecycle is complete
                    break
            else:
                log.logger.warning(f"{self.name}: received_message: no matching teleport protocol for msg={msg} from {src}")

        elif msg.msg_type is TeleportMsgType.ACK:              # Alice receives acknowledgment from Bob
            for teleport_protocol in self.teleport_protocols:  # find the correct teleport protocol on Alice's side
                if src == teleport_protocol.remote_node_name and msg.bob_comm_memory_name == teleport_protocol.bob_comm_memory_name:
                    self.node.resource_manager.expire_rules_by_reservation(msg.reservation)                      # expire the rules
                    self.node.resource_manager.update(None, teleport_protocol.alice_comm_memory, MemoryInfo.RAW) # release the alice comm memory
                    self.teleport_protocols.remove(teleport_protocol)  # remove the protocol instance, it's lifecycle is complete
                    break
            else:
                log.logger.warning(f"{self.name}: received_message: no matching teleport protocol for msg={msg} from {src}")

    def teleport_complete(self, comm_key: int):
        """Called by TeleportProtocol once Bob's qubit is corrected. comm_key holds the teleported |ψ⟩.

        Args:
            comm_key (int): The key of the comm memory where the teleported state is stored.
        """
        my_qubit = self.node.timeline.quantum_manager.get(comm_key)
        psi = my_qubit.state # get qubit state
        log.logger.info(f"{self.name}: teleport done, state={psi}")
        self.results.append((self.node.timeline.now(), psi)) # append result (timestamp, state)
