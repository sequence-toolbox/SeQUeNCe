"""
ControlledUApp
==============

A tiny SeQUeNCe application that implements an *arbitrary* controlled-U
(two-party) gate.

•  The **control** node measures its Bell-pair qubit and sends the two
   classical bits (m1, m2) to the **target** node.

•  The **target** node stores its half of the Bell pair and, once it
   receives the classical message, applies *U* **iff** m1 == 1, then
   measures.

The app is intentionally minimal – it leaves Bell-pair generation /
reservation to an outer workflow (or to the test harness).
"""

from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from sequence.app.request_app        import RequestApp
from sequence.message                import Message
from sequence.components.circuit     import Circuit

if TYPE_CHECKING:                         # avoid import cycles at runtime
    from sequence.topology.node          import QuantumRouter
    from sequence.resource_management.memory_manager import MemoryInfo


# ────────────────────────── classical payload ────────────────────────────
class ControlMessage(Message):
    """Classical message carrying the two Bell-measurement bits."""
    def __init__(self, receiver: str, mem_idx: int, m1: int, m2: int):
        super().__init__("CTRL-U", receiver)
        self.idx  = mem_idx        # Which memory on the target node
        self.m1   = m1             # Z-basis measurement of control qubit
        self.m2   = m2             # X-basis measurement of entangled qubit


# ──────────────────────────── the application ────────────────────────────
class ControlledUApp(RequestApp):
    """
    Parameters
    ----------
    unitary_fn : Callable[[Circuit], None]
        A function that receives a *fresh* single-qubit ``Circuit`` and
        should append the desired *U* gate onto qubit 0.

        Examples
        --------
        ```python
        def apply_rx_pi_over_4(circ):
            circ.rx(0, math.pi / 4)

        app = ControlledUApp(node, "ctrl", "tgt", apply_rx_pi_over_4)
        ```
    """
    def __init__(self,
                 node:        "QuantumRouter",
                 name:        str,
                 peer_name:   str,
                 unitary_fn:  Callable[[Circuit], None]):
        super().__init__(node)
        self.set_name(name)
        self.peer_name   = peer_name
        self.unitary_fn  = unitary_fn

        # Register ourselves in the node’s protocol stack
        node.protocols.append(self)

        self.pending: dict[int, "MemoryInfo"] = {}  # idx -> MemoryInfo
        self.results: list[int]               = []  # measurement outcomes (0 / 1)

    # ───────────────── RM callback ─────────────────
    def get_memory(self, info: "MemoryInfo") -> None:
        """
        Called by the Resource-Manager when a Bell-pair memory arrives.
        We simply store it until the classical control message shows up.
        """
        if info.state == "ENTANGLED":
            self.pending[info.index] = info.memory

    # ───────────────── classical callback ──────────
    def received_message(self, _src: str, msg: ControlMessage) -> None:
        mem = self.pending.pop(msg.idx, None)
        if mem is None:                       # unknown / already used
            return

        # Build a tiny circuit:  (apply U iff m1==1) ➜ measure
        circ = Circuit(1)
        if msg.m1 == 1:                       # control was |1⟩ ➜ apply U
            self.unitary_fn(circ)
        circ.measure(0)

        qm   = self.node.timeline.quantum_manager
        rand = self.node.get_generator().random()
        res  = qm.run_circuit(circ, [mem.qstate_key], rand)[mem.qstate_key]

        self.results.append(res)

        self.node.resource_manager.update(None, mem, "RAW")
    def entangle_and_measure(self, ctrl_key: int, bell_key: int) -> tuple[int, int]:
        circ = Circuit(2)
        circ.cx(0, 1)
        circ.h(0)
        circ.measure(0)
        circ.measure(1)

        qm = self.node.timeline.quantum_manager
        rnd = self.node.get_generator().random()
        res = qm.run_circuit(circ, [ctrl_key, bell_key], rnd)
        return res[ctrl_key], res[bell_key]
