""" Test for Quantum Teleportation Application
This script tests the quantum teleportation application by simulating a simple two-node network.
It verifies that the teleportation process correctly recreates the original quantum state.
"""
import math
import numpy as np
from sequence.topology.dqc_net_topo import DQCNetTopo
from sequence.app.teleport_app import TeleportApp
from sequence.constants import MILLISECOND

def single_trial(psi):
    """Run a single trial of teleportation with the given quantum state psi.
    Args:       
        psi (np.ndarray): The quantum state to teleport, represented as a numpy array.
    Returns:     
        np.ndarray: The quantum state after teleportation, as received by Bob.
    """
    # set up the 2-node network
    topo = DQCNetTopo("tests/app/teleport_2node.json")
    tl   = topo.tl
    nodes = topo.nodes[DQCNetTopo.DQC_NODE]
    alice = next(n for n in nodes if n.name=="router_0")
    bob   = next(n for n in nodes if n.name=="router_1")
    # 1) Prepare |ψ> in Alice’s data qubit
    # a_key = alice.components["data_mem"].memories[0].qstate_key
    # alice.timeline.quantum_manager.set([a_key], psi)
    # memory = alice.components["data_mem"].memories[0]
    memory_arr = tl.get_entity_by_name(alice.data_memo_arr_name)
    memory_arr[0].update_state(psi)

    # 2) Attach the TeleportApp on both nodes
    A = TeleportApp(alice)
    B = TeleportApp(bob)

    # 3) Kick off teleport
    A.start(
        responder   = bob.name,
        start_t     = 10  * MILLISECOND,
        end_t       = 30 * MILLISECOND,
        memory_size = 1,
        fidelity    = 0.8,
        data_src    = 0
    )
    # 4) Run the simulation
    tl.init()
    tl.run()
    # 5) Read out Bob’s data qubit state
    teleported_qubit = B.results[0]
    return np.array(teleported_qubit)

def test_teleport_recreates_state():
    """Test that the teleportation process correctly recreates the original quantum state.
        This function runs a single trial of teleportation with a specific quantum state and checks
        if the teleported state matches the original state."""
    # teleport this arbitrary superposition
    psi = np.array([math.sqrt(3)/2, 0.5])
    out = single_trial(psi)

    # check that Bob's final state matches the original |ψ⟩
    assert out.shape == psi.shape
    assert np.allclose(out, psi, atol=1e-6), f"teleported state {out} != original {psi}"

test_teleport_recreates_state()
