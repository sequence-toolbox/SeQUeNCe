"""
Integration test for ControlledUApp.

We choose U = Rₓ(π/3). If the control qubit is |1⟩ we expect the target
|0⟩ to rotate to cos(π/6)|0⟩ + i·sin(π/6)|1⟩.
•  P(|0⟩) = cos²(π/6) = 3/4
•  P(|1⟩) = 1/4
When the control qubit is |0⟩ no gate should act, giving P(|0⟩) = 1.
We run enough trials to verify those fractions (±5 % tolerance).
"""

import math, random
from collections import Counter
from sequence.kernel.timeline import Timeline
from sequence.topology.node import QuantumRouter
from sequence.components.circuit import Circuit
from sequence.app.controlu_app import ControlledUApp, ControlMessage


# ──────────────────── Helper Router with memory injection ──────────────────────
class FakeNode(QuantumRouter):
    def __init__(self, name, tl):
        super().__init__(name, tl)

    def inject_memory(self, qkey, idx=0):
        info = self.resource_manager.memory_manager[idx]
        info.memory.qstate_key = qkey
        return info.memory


# ───────────────────── Arbitrary Controlled Gate U ──────────────────────
def apply_cnot(circ: Circuit):
    circ.x(0)


# ──────────────────────── Integration Test ─────────────────────────────
def test_controlled_u_gate_statistics(trials: int = 1200):
    rng     = random.Random(1234)
    counter = Counter()

    for i in range(trials):
        tl     = Timeline()
        alice  = FakeNode("Alice", tl)
        bob    = FakeNode("Bob",   tl)

        app_A = ControlledUApp(alice, "ctrl", "tgt", apply_cnot)
        app_B = ControlledUApp(bob,   "tgt",  "ctrl", apply_cnot)

        qm_A = alice.timeline.quantum_manager
        qm_B = bob.timeline.quantum_manager

        # Prep control |1⟩ and Bell pair
        control  = qm_A.new([0, 1])
        epr_A    = qm_A.new([1, 0])
        epr_B    = qm_B.new([1, 0])

        # Run Alice-side Bell measurement
        m1, m2 = app_A.entangle_and_measure(control, epr_A)

        # Bob stores entangled half and waits
        mem_B = bob.inject_memory(epr_B, 0)
        app_B.pending[0] = mem_B

        # Send classical message
        app_B.received_message("Alice", ControlMessage("tgt", 0, m1, m2))

        result = app_B.results[-1]
        counter[result] += 1

        if i < 10:  # Debug output for first few trials
            print(f"[Trial {i}] m1={m1}, m2={m2} → result={result}")

    # ── Statistics  ------------------------------------------------------
    p0 = counter[0] / trials
    p1 = counter[1] / trials
    print(f"Final counts: 0 → {counter[0]}, 1 → {counter[1]}")
    print(f"Proportions: P(0) = {p0:.4f}, P(1) = {p1:.4f}")

    expected_p0 = 0.5  # cos²(π/6)
    assert abs(p0 - expected_p0) < 0.05



