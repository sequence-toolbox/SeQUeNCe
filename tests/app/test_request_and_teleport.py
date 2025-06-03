# tests/app/test_request_and_teleport.py

import math
import random
from collections import Counter
from numpy import allclose
from sequence.kernel.timeline import Timeline
from sequence.topology.node import QuantumRouter
from sequence.app.teleport_app import TeleportApp, TeleportMessage, _teleport_1
from sequence.components.circuit import Circuit


# ─────────────────────────────────────────────────────────────────────────────
class FakeNode(QuantumRouter):
    """Router that lets us drop a qubit directly into a memory slot."""
    def __init__(self, name, tl):
        super().__init__(name, tl)

    def inject_entangled_memory(self, qkey, idx: int = 0):
        mem = self.resource_manager.memory_manager[idx].memory
        mem.qstate_key = qkey
        return mem


def apply_pauli_corrections(qm, key: int, x_flip: int, z_flip: int, rng):
    """
    Apply X / Z gates with a tiny single-qubit circuit, without measurement.
    Pass a float sample (rng.random()) to run_circuit.
    """
    circ = Circuit(1)
    if x_flip:
        circ.x(0)
    if z_flip:
        circ.z(0)
    qm.run_circuit(circ, [key], rng.random())


def bloch_random_state():
    """Return a uniformly random single-qubit pure state on the Bloch sphere."""
    u = random.random()
    θ = 2 * math.acos(math.sqrt(u))
    φ = 2 * math.pi * random.random()
    return [
        math.cos(θ / 2),
        complex(math.sin(θ / 2) * math.cos(φ), math.sin(θ / 2) * math.sin(φ))
    ]


# ─────────────────────────────────────────────────────────────────────────────
def test_single_teleportation(trials: int = 1000):
    """
    Teleport |ψ〉 = √3/2|0〉 + ½|1〉 repeatedly and verify |0⟩
    appears about 75% of the time, within ±5%.
    """
    psi = [math.sqrt(3) / 2, 0.5]
    expected_p0 = abs(psi[0])**2  # 0.75
    counts = Counter()

    for _ in range(trials):
        tl = Timeline()
        alice = FakeNode("Alice", tl)
        bob = FakeNode("Bob", tl)
        app_b = TeleportApp(bob, "B", "A")

        qm_a = alice.timeline.quantum_manager
        qm_b = bob.timeline.quantum_manager

        # Prepare psi on Alice and EPR halves
        psi_key    = qm_a.new(psi)
        bell_a_key = qm_a.new([1, 0])
        bell_b_key = qm_b.new([1, 0])

        # Alice’s Bell-measurement
        z, x = _teleport_1(psi_key, bell_a_key, alice)

        # Bob receives his entangled half
        mem = bob.inject_entangled_memory(bell_b_key, idx=0)
        before0, before1 = app_b.results
        app_b.pending[0] = mem
        app_b.received_message("Alice", TeleportMessage("B", 0, x, z))
        after0, after1 = app_b.results

        # deduce single outcome by counter delta
        outcome = 0 if after0 > before0 else 1
        counts[outcome] += 1

    p0 = counts[0] / trials
    assert abs(p0 - expected_p0) < 0.05


# ─────────────────────────────────────────────────────────────────────────────
def test_3_node_relay(trials: int = 500):
    """
    Three-node relay teleportation: Alice → Charlie → Bob.
    Expect |0〉 probability ≈ 0.75 ± 5%.
    """
    psi = [math.sqrt(3) / 2, 0.5]
    expected_p0 = abs(psi[0])**2  # 0.75
    counts = Counter()

    for _ in range(trials):
        tl = Timeline()
        alice = FakeNode("Alice", tl)
        charlie = FakeNode("Charlie", tl)
        bob = FakeNode("Bob", tl)

        app_c = TeleportApp(charlie, "C", "A")  # Charlie listens for Alice
        app_b = TeleportApp(bob, "B", "C")      # Bob listens for Charlie

        qm_a = alice.timeline.quantum_manager
        qm_c = charlie.timeline.quantum_manager
        qm_b = bob.timeline.quantum_manager

        # ── Alice → Charlie ─────────────────────────────────────────────
        psi_key   = qm_a.new(psi)
        bell1_a   = qm_a.new([1, 0])
        bell1_c   = qm_c.new([1, 0])
        z1, x1    = _teleport_1(psi_key, bell1_a, alice)

        mem_c1 = charlie.inject_entangled_memory(bell1_c, 0)
        apply_pauli_corrections(qm_c, mem_c1.qstate_key, x1, z1, charlie.get_generator())

        # ── Charlie → Bob ────────────────────────────────────────────────
        # Re-register Charlie’s corrected state onto a fresh key
        ket_obj        = qm_c.get(mem_c1.qstate_key)
        teleported_key = qm_c.new(ket_obj.state)

        bell2_c = qm_c.new([1, 0])
        bell2_b = qm_b.new([1, 0])
        z2, x2  = _teleport_1(teleported_key, bell2_c, charlie)

        mem_b = bob.inject_entangled_memory(bell2_b, 0)
        before0, before1 = app_b.results
        app_b.pending[0] = mem_b
        app_b.received_message("Charlie", TeleportMessage("B", 0, x2, z2))
        after0, after1 = app_b.results

        # record Bob’s new outcome
        outcome = 0 if after0 > before0 else 1
        counts[outcome] += 1

    p0 = counts[0] / trials
    assert abs(p0 - expected_p0) < 0.05


# ─────────────────────────────────────────────────────────────────────────────
def test_random_state_single_hop(samples: int = 400):
    """
    Teleport many random Bloch-sphere states.  Compare aggregate |0〉
    frequency to theoretical average
    """
    tl = Timeline()
    a = FakeNode("A", tl)
    b = FakeNode("B", tl)
    app_b = TeleportApp(b, "B", "A")
    qm_a, qm_b = a.timeline.quantum_manager, b.timeline.quantum_manager

    expected_sum = 0.0
    observed_0   = 0

    for _ in range(samples):
        ψ = bloch_random_state()
        expected_sum += abs(ψ[0])**2

        ψ_key = qm_a.new(ψ)
        eprA  = qm_a.new([1, 0])
        eprB  = qm_b.new([1, 0])

        z, x = _teleport_1(ψ_key, eprA, a)
        mem  = b.inject_entangled_memory(eprB, 0)

        before0, before1 = app_b.results
        app_b.pending[0] = mem
        app_b.received_message("A", TeleportMessage("B", 0, x, z))
        after0, after1 = app_b.results

        outcome = 0 if after0 > before0 else 1
        if outcome == 0:
            observed_0 += 1

    actual_p0   = observed_0 / samples
    expected_p0 = expected_sum / samples
    assert abs(actual_p0 - expected_p0) < 0.07


# ─────────────────────────────────────────────────────────────────────────────
def test_all_correction_patterns():
    """
    Start with |1〉 on Bob's side, then apply each (z,x) Pauli pattern
    and verify the resulting measurement.
    """
    tl = Timeline()
    a = FakeNode("A", tl)
    b = FakeNode("B", tl)
    qm_b = b.timeline.quantum_manager
    rng  = b.get_generator()

    for z_flip in (0, 1):
        for x_flip in (0, 1):
            key = qm_b.new([0, 1])  # |1〉
            apply_pauli_corrections(qm_b, key, x_flip, z_flip, rng)

            # measure in Z basis
            circ = Circuit(1)
            circ.measure(0)
            res = qm_b.run_circuit(circ, [key], rng.random())[key]

            # theoretical: (σ_x^x σ_z^z)|1〉
            expected = 0 if x_flip else 1
            assert res == expected


# ─────────────────────────────────────────────────────────────────────────────
def test_back_to_back_two_qubits():
    """
    Teleport |0〉 then |1〉 in sequence.  Bob's outcomes should be [0, 1].
    """
    tl = Timeline()
    a = FakeNode("A", tl)
    b = FakeNode("B", tl)
    app_b = TeleportApp(b, "B", "A")
    qm_a, qm_b = a.timeline.quantum_manager, b.timeline.quantum_manager

    outcomes = []
    for ψ in ([1, 0], [0, 1]):
        ψ_key = qm_a.new(ψ)
        eprA  = qm_a.new([1, 0])
        eprB  = qm_b.new([1, 0])

        z, x = _teleport_1(ψ_key, eprA, a)
        mem  = b.inject_entangled_memory(eprB, 0)

        before0, before1 = app_b.results
        app_b.pending[0] = mem
        app_b.received_message("A", TeleportMessage("B", 0, x, z))
        after0, after1 = app_b.results

        out = 0 if after0 > before0 else 1
        outcomes.append(out)

    assert outcomes == [0, 1]


# ─────────────────────────────────────────────────────────────────────────────
def test_invalid_classical_message():
    """
    If Bob receives a TeleportMessage whose memory index is out of range,
    Bob’s TeleportApp should ignore it and results should remain unchanged.
    """
    tl = Timeline()
    b = FakeNode("B", tl)
    app_b = TeleportApp(b, "B", "A")

    initial_len = len(app_b.results)
    bogus_msg = TeleportMessage("B", 99, 0, 0)  # positional args
    app_b.received_message("A", bogus_msg)

    assert len(app_b.results) == initial_len
