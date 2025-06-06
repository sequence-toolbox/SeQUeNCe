"""
Minimal TeleportApp that works with SeQUeNCe's current Circuit / QuantumManager API
(no Circuit.run or set_qubit_indices). It teleports a qubit whenever a Bell pair
becomes available and a classical correction message arrives.
"""

from __future__ import annotations
from typing import Tuple, TYPE_CHECKING
from numpy import sqrt

from sequence.app.request_app import RequestApp
from sequence.message import Message
from sequence.components.circuit import Circuit
from sequence.components.memory import Memory

if TYPE_CHECKING:
    from sequence.topology.node import QuantumRouter
    from sequence.resource_management.memory_manager import MemoryInfo


# ───────────────────────── Classical Message Format ─────────────────────────

class TeleportMessage(Message):
    """
    Classical message used to convey the Pauli corrections (x, z) from
    sender to receiver during teleportation.
    """
    def __init__(self, receiver: str, mem_idx: int, x_flip: int, z_flip: int):
        super().__init__("TELEPORT", receiver)
        self.idx = mem_idx         # Index of memory in receiver's memory manager
        self.x_flip = x_flip       # Whether to apply X correction
        self.z_flip = z_flip       # Whether to apply Z correction


# ──────────────────────────── Main Teleport App ─────────────────────────────

class TeleportApp(RequestApp):
    """
    Minimal teleportation application that runs on a QuantumRouter.
    It teleports a fixed qubit state whenever a Bell pair and correction
    message become available.
    """
    def __init__(self, node: "QuantumRouter", name: str, peer_name: str):
        super().__init__(node)
        self.set_name(name)             # Assign app name
        self.peer_name = peer_name      # Name of the remote node
        node.protocols.append(self)     # Register this app on the node
        self.pending = {}               # Memory index → Memory object (awaiting message)
        self.results = [0, 0]           # Number of times receiver measured 0 or 1

    def get_memory(self, info: "MemoryInfo") -> None:
        """
        Called when an entangled memory becomes available.
        If this node initiated the entanglement, teleport the known state.
        Otherwise, store the memory until the classical correction arrives.
        """
        if info.state != "ENTANGLED":
            return

        res = self.memo_to_reserve.get(info.index)

        if res and res.initiator == self.node.name:
            # If initiator: embed known state into this qubit and teleport it
            ent_key = info.memory.qstate_key
            qm = self.node.timeline.quantum_manager
            qm.set(ent_key, [sqrt(3)/2, 0.5])  # Known state |ψ⟩

            z, x = self._teleport_1(ent_key, ent_key)
            msg = TeleportMessage(self.peer_name, info.remote_memo, x, z)
            self.node.send_message(res.responder, msg)
            self.node.resource_manager.update(None, info.memory, "RAW")

        else:
            # Otherwise, wait for classical message from sender
            self.pending[info.index] = info.memory

    def received_message(self, _src: str, msg: TeleportMessage) -> None:
        """
        Called when a classical message (Pauli corrections) is received.
        Applies the corrections to the entangled memory and measures it.
        """
        mem = self.pending.pop(msg.idx, None)
        if mem is None:
            return

        # Apply corrections and measure
        outcome = self._teleport_2(mem.qstate_key, msg.x_flip, msg.z_flip)
        self.results[outcome] += 1

        # Mark memory as raw again after use
        self.node.resource_manager.update(None, mem, "RAW")

    def _teleport_1(self, psi_key: int, ent_key: int) -> Tuple[int, int]:
        """
        Alice's side of teleportation: entangle and Bell-measure.
        Returns z and x correction bits.
        """
        qm = self.node.timeline.quantum_manager
        rnd = self.node.get_generator().random()

        circ = Circuit(2)
        circ.cx(0, 1)
        circ.h(0)
        circ.measure(0)
        circ.measure(1)

        res = qm.run_circuit(circ, [psi_key, ent_key], rnd)
        return res[psi_key], res[ent_key]

    def _teleport_2(self, ent_key: int, x: int, z: int) -> int:
        """
        Bob's side of teleportation: apply corrections and measure.
        Returns the final measurement result (0 or 1).
        """
        qm = self.node.timeline.quantum_manager
        rnd = self.node.get_generator().random()

        circ = Circuit(1)
        if x:
            circ.x(0)
        if z:
            circ.z(0)
        circ.measure(0)

        res = qm.run_circuit(circ, [ent_key], rnd)
        return res[ent_key]

    def apply_pauli_corrections(self, key: int, x_flip: int, z_flip: int) -> None:
        """
        Helper for testing: applies X/Z Pauli corrections to a single qubit.
        """
        qm = self.node.timeline.quantum_manager
        circ = Circuit(1)
        if x_flip:
            circ.x(0)
        if z_flip:
            circ.z(0)
        qm.run_circuit(circ, [key], self.node.get_generator().random())







