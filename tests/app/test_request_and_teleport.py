import math
import random
from collections import Counter
from numpy import allclose

from sequence.kernel.timeline import Timeline
from sequence.topology.node import QuantumRouter
from sequence.app.teleport_app import TeleportApp, TeleportMessage
from sequence.components.circuit import Circuit
from sequence.utils.random_state import random_state


# ────────────────────────────────
# FakeNode simulates a quantum router with ability to inject qubits
# directly into its memory manager for testing purposes
class FakeNode(QuantumRouter):
    def __init__(self, name, tl):
        super().__init__(name, tl)

    def inject_entangled_memory(self, qkey, idx: int = 0):
        mem = self.resource_manager.memory_manager[idx].memory
        mem.qstate_key = qkey
        return mem


# ────────────────────────────────
# Test 1: Basic correctness of teleporting a known state
def test_single_teleportation(trials: int = 1000):
    psi = [math.sqrt(3) / 2, 0.5]          # Known state: expect ~75% |0⟩
    expected_p0 = abs(psi[0])**2
    counts = Counter()

    for _ in range(trials):
        # Setup
        tl = Timeline()
        alice = FakeNode("Alice", tl)
        bob = FakeNode("Bob", tl)
        app_a = TeleportApp(alice, "A", "B")
        app_b = TeleportApp(bob,   "B", "A")

        qm_a = alice.timeline.quantum_manager
        qm_b = bob.timeline.quantum_manager

        # Initialize qubits
        psi_key    = qm_a.new(psi)
        bell_a_key = qm_a.new([1, 0])
        bell_b_key = qm_b.new([1, 0])

        # Alice's Bell measurement
        z, x = app_a._teleport_1(psi_key, bell_a_key)

        # Bob receives memory and classical message
        mem = bob.inject_entangled_memory(bell_b_key, idx=0)
        before0, before1 = app_b.results
        app_b.pending[0] = mem
        app_b.received_message("Alice", TeleportMessage("B", 0, x, z))
        after0, after1 = app_b.results

        # Record outcome
        outcome = 0 if after0 > before0 else 1
        counts[outcome] += 1

    p0 = counts[0] / trials
    assert abs(p0 - expected_p0) < 0.05


# ────────────────────────────────
# Test 2: Ensure each Pauli correction combination yields correct results
def test_all_correction_patterns():
    tl = Timeline()
    a = FakeNode("A", tl)
    b = FakeNode("B", tl)
    app = TeleportApp(b, "B", "A")
    qm = b.timeline.quantum_manager
    rng = b.get_generator()

    for z_flip in (0, 1):
        for x_flip in (0, 1):
            key = qm.new([0, 1])  # Start with |1⟩
            app.apply_pauli_corrections(key, x_flip, z_flip)

            # Measure and verify theoretical result
            circ = Circuit(1)
            circ.measure(0)
            res = qm.run_circuit(circ, [key], rng.random())[key]
            expected = 0 if x_flip else 1
            assert res == expected


# ────────────────────────────────
# Test 3: Send two qubits back-to-back and confirm ordering is preserved
def test_back_to_back_two_qubits():
    tl = Timeline()
    a = FakeNode("A", tl)
    b = FakeNode("B", tl)
    app_b = TeleportApp(b, "B", "A")
    qm_a, qm_b = a.timeline.quantum_manager, b.timeline.quantum_manager
    outcomes = []

    for ψ in ([1, 0], [0, 1]):  # Teleport |0⟩ then |1⟩
        ψ_key = qm_a.new(ψ)
        eprA  = qm_a.new([1, 0])
        eprB  = qm_b.new([1, 0])
        app_a = TeleportApp(a, "A", "B")
        z, x = app_a._teleport_1(ψ_key, eprA)
        mem  = b.inject_entangled_memory(eprB, 0)

        before0, before1 = app_b.results
        app_b.pending[0] = mem
        app_b.received_message("A", TeleportMessage("B", 0, x, z))
        after0, after1 = app_b.results
        out = 0 if after0 > before0 else 1
        outcomes.append(out)

    assert outcomes == [0, 1]


# ────────────────────────────────
# Test 4: Ignore invalid classical messages (no pending memory)
def test_invalid_classical_message():
    tl = Timeline()
    b = FakeNode("B", tl)
    app_b = TeleportApp(b, "B", "A")
    initial_len = len(app_b.results)

    # Index 99 does not exist
    bogus_msg = TeleportMessage("B", 99, 0, 0)
    app_b.received_message("A", bogus_msg)
    assert len(app_b.results) == initial_len


# ────────────────────────────────
# Test 5: Teleport many random states and verify average correctness
def test_random_state_single_hop(samples: int = 400):
    tl = Timeline()
    a = FakeNode("A", tl)
    b = FakeNode("B", tl)
    app_b = TeleportApp(b, "B", "A")
    qm_a, qm_b = a.timeline.quantum_manager, b.timeline.quantum_manager

    expected_sum = 0.0
    observed_0 = 0

    for _ in range(samples):
        ψ = random_state()
        expected_sum += abs(ψ[0])**2

        ψ_key = qm_a.new(ψ)
        eprA  = qm_a.new([1, 0])
        eprB  = qm_b.new([1, 0])

        app_a = TeleportApp(a, "A", "B")
        z, x = app_a._teleport_1(ψ_key, eprA)
        mem  = b.inject_entangled_memory(eprB, 0)

        before0, before1 = app_b.results
        app_b.pending[0] = mem
        app_b.received_message("A", TeleportMessage("B", 0, x, z))
        after0, after1 = app_b.results

        outcome = 0 if after0 > before0 else 1
        if outcome == 0:
            observed_0 += 1

    actual_p0 = observed_0 / samples
    expected_p0 = expected_sum / samples
    assert abs(actual_p0 - expected_p0) < 0.07

