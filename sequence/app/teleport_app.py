""" TeleportApp Module
This module implements the TeleportApp class, which is responsible for managing quantum teleportation
between quantum nodes. It utilizes the TeleportProtocol to handle the teleportation process,
including the reservation of entangled pairs and the application of corrections based on classical messages.
"""
from .request_app import RequestApp
from ..utils import log
from ..entanglement_management.teleportation import TeleportProtocol, TeleportMessage
from ..topology.node import DQCNode


class TeleportApp(RequestApp):
    """Code for the teleport application.

    TeleportApp is a specialized RequestApp that implements quantum teleportation.
    It handles the teleportation protocol between two quantum nodes (Alice and Bob).

    Attributes:
        node (DQCNode): The quantum node this app is attached to.
        name (str): The name of the teleport application.
        results (list): List to store the results of teleportation.
        teleport_protocol (TeleportProtocol): The teleportation protocol instance.
    """
    def __init__(self, node: DQCNode):
        super().__init__(node)
        self.name = f"{self.node.name}.TeleportApp"
        node.teleport_app = self   # register ourselves so incoming TeleportMessage lands here:
        self.results = []          # where we’ll collect Bob’s teleported state
        self.teleport_protocol = TeleportProtocol(owner=node, data_src=None)  # create a single protocol instance, on both Alice & Bob
        log.logger.debug(f"{self.name}: initialized")

    def start(self, responder: str, start_t: int, end_t: int, memory_size: int, fidelity: float, data_src: int):
        """Start the teleportation process.

        Args: 
            responder (str): Name of the responder node (Bob).
            start_t (int): Start time of the teleportation (in ps).
            end_t (int): End time of the teleportation (in ps).
            memory_size (int): Size of the memory used for the teleportation.
            fidelity (float): Target fidelity of the teleportation.
            data_src (int): Index of the data qubit to be teleported.
        """
        # configure our single protocol
        self.teleport_protocol.data_src     = data_src
        self.teleport_protocol.is_initiator = (self.node.name != responder)
        self.teleport_protocol.remote       = responder

        # cache Alice’s data‐qubit key for the Bell measurement
        memory_array = self.node.get_component_by_name(self.node.data_memo_arr_name)
        data_memory = memory_array[data_src]
        self.teleport_protocol.data_memory = data_memory
        self.teleport_protocol._q_data     = data_memory.qstate_key

        log.logger.debug(f"{self.name}: start() → responder={responder}, data_src={data_src}")

        # reserve and generate EPR pair
        super().start(responder, start_t, end_t, memory_size, fidelity)

        # notify the protocol we’re kicking off
        self.teleport_protocol.start()

    def get_reservation_result(self, reservation, result: bool):
        """Handle the reservation result from the network manager.

        Args:
            reservation (Reservation): The reservation object.
            result (bool): True if the reservation was successful, False otherwise.
        """
        super().get_reservation_result(reservation, result)
        log.logger.debug(f"{self.name}: reservation_result → {result}")

    def get_memory(self, info):
        """Handle memory state changes.

        Args:
            info (MemoryInfo): Information about the memory state change.
        """
        log.logger.debug(f"{self.name}: get_memory(idx={info.index}, state={info.state})")
        # once we see our entangled half, hand it to the protocol
        if info.index in self.memo_to_reservation:
            if info.state == "ENTANGLED":
                self.teleport_protocol.handle_entangled(info, self.memo_to_reservation[info.index])

    def received_message(self, src: str, msg: TeleportMessage):
        """Handle incoming teleport messages.

        Args:
            src (str): Source node name.
            msg (TeleportMessage): The teleport message received.
        """
        log.logger.debug(f"{self.name} received_message from {src}: {msg}")
        # feed Bob’s corrections into the protocol
        self.teleport_protocol.received_message(src, msg)

    def teleport_complete(self, comm_key: int):
        """Called by TeleportProtocol once Bob's qubit is corrected. comm_key holds the teleported |ψ⟩.

        Args:
            comm_key (int): The key of the comm memory where the teleported state is stored.
        """
        my_qubit  = self.node.timeline.quantum_manager.get(comm_key)
        psi = my_qubit.state # get qubit state
        log.logger.info(f"{self.name}: teleport done, state={psi}")
        self.results.append(psi) #append result to the list
