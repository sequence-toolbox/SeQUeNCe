"""
Minimal TeleportApp that works with SeQUeNCe's current Circuit / QuantumManager API
(no Circuit.run or set_qubit_indices).  It teleports a qubit whenever a Bell pair
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


# ───────────────────────── helper circuits ──────────────────────────
def _teleport_1(psi_key: int, ent_key: int, node: "QuantumRouter") -> Tuple[int, int]:
    """Sender-side: entangle |ψ⟩ with local half of Bell pair and Bell-measure."""
    qm = node.timeline.quantum_manager
    rnd = node.get_generator().random()

    circ = Circuit(2)
    circ.cx(0, 1)
    circ.h(0)
    circ.measure(0)
    circ.measure(1)

    res = qm.run_circuit(circ, [psi_key, ent_key], rnd)
    z_flip = res[psi_key]    # measurement of qubit-0
    x_flip = res[ent_key]    # measurement of qubit-1
    return z_flip, x_flip


def _teleport_2(ent_key: int, node: "QuantumRouter", x: int, z: int) -> int:
    """Receiver-side: apply X/Z corrections then measure."""
    qm  = node.timeline.quantum_manager
    rnd = node.get_generator().random()

    circ = Circuit(1)
    if x:
        circ.x(0)
    if z:
        circ.z(0)
    circ.measure(0)

    res = qm.run_circuit(circ, [ent_key], rnd)
    return res[ent_key]      # 0 or 1


# ───────────────────────── classical payload ────────────────────────
class TeleportMessage(Message):
    def __init__(self, receiver: str, mem_idx: int, x_flip: int, z_flip: int):
        super().__init__("TELEPORT", receiver)
        self.idx, self.x_flip, self.z_flip = mem_idx, x_flip, z_flip


# ───────────────────────── application class ────────────────────────
class TeleportApp(RequestApp):
    """
    Very small app:  when a Bell-pair memory arrives it teleports a fresh
    |ψ⟩ from the initiator to the responder.  Results are counted in
    self.results[0] and self.results[1].
    """
    def __init__(self, node: "QuantumRouter", name: str, peer_name: str):
        super().__init__(node)
        self.set_name(name)
        self.peer_name = peer_name
        node.protocols.append(self)

        self.pending: dict[int, "Memory"] = {}   # idx → memory waiting for bits
        self.results = [0, 0]                    # counts of 0 / 1 outcomes

    # called by RM when a memory is delivered
    def get_memory(self, info: "MemoryInfo") -> None:
        if info.state != "ENTANGLED":
            return

        # if we are the initiator of the reservation: teleport immediately
        res = self.memo_to_reserve.get(info.index)
        if res and res.initiator == self.node.name:
            ent_key = info.memory.qstate_key

            # overwrite Alice’s half with arbitrary |ψ⟩ (example) just for demo:
            qm = self.node.timeline.quantum_manager
            qm.set(ent_key, [sqrt(3)/2, 0.5])    # arbitrary single-qubit state

            z, x = _teleport_1(ent_key, ent_key, self.node)
            msg  = TeleportMessage(self.peer_name, info.remote_memo, x, z)
            self.node.send_message(res.responder, msg)

            self.node.resource_manager.update(None, info.memory, "RAW")

        else:
            # we are the receiver: stash memory until classical bits arrive
            self.pending[info.index] = info.memory

    # called when correction bits arrive
    def received_message(self, _src: str, msg: TeleportMessage) -> None:
        mem = self.pending.pop(msg.idx, None)
        if mem is None:
            return
        outcome = _teleport_2(mem.qstate_key, self.node, msg.x_flip, msg.z_flip)
        self.results[outcome] += 1
        self.node.resource_manager.update(None, mem, "RAW")





