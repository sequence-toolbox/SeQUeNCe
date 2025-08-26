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

    # import sequence.utils.log as log
    # log_filename = 'test_teleport.log'
    # log.set_logger(__name__, tl, log_filename)
    # log.set_logger_level('DEBUG')
    # modules = ['generation', 'teleport_app', 'teleportation']
    # for module in modules:
    #     log.track_module(module)

    nodes = topo.nodes[DQCNetTopo.DQC_NODE]
    alice = next(n for n in nodes if n.name=="alice")
    bob   = next(n for n in nodes if n.name=="bob")

    # 1) Prepare |ψ> in Alice’s data qubit
    data_memo_arr = alice.get_component_by_name(alice.data_memo_arr_name)
    data_memo_arr[0].update_state(psi)

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
        data_memory_index = 0
    )

    # 4) Run the simulation
    tl.init()
    tl.run()

    # 5) Read out Bob’s data qubit state
    teleported_qubit = B.results[0][1]  # each result is (timestamp, state)
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




"""
Dual-teleport test (3 nodes): Alice teleports to Bob and Charlie concurrently.

We prepare two different states on Alice's data memories:
- data[0] -> (to Bob)
- data[1] -> (to Charlie)

A single TeleportApp is attached to Alice and .start(...) is called twice.
Bob and Charlie each get their own TeleportApp to record results.
"""



def dual_trial(psi_b: np.ndarray, psi_c: np.ndarray):
    """Run a dual-teleport trial on a 3-node network (alice, bob, charlie).
    Args:
        psi_b: state to send to Bob
        psi_c: state to send to Charlie
    Returns:
        (out_b, out_c): teleported states measured at Bob and Charlie
    """
    topo = DQCNetTopo("tests/app/teleport_3node.json")
    tl   = topo.tl

    # log_filename = 'tmp/test_teleport_10.log'
    # log.set_logger(__name__, tl, log_filename)
    # log.set_logger_level('INFO')
    # # modules = ['generation', 'teleport_app', 'teleportation', 'network_manager', 'resource_manager']
    # modules = ['generation', 'teleport_app', 'teleportation']

    # for module in modules:
    #     log.track_module(module)

    nodes   = topo.nodes[DQCNetTopo.DQC_NODE]
    alice   = next(n for n in nodes if n.name == "alice")
    bob     = next(n for n in nodes if n.name == "bob")
    charlie = next(n for n in nodes if n.name == "charlie")

    # Prepare |psi_b> and |psi_c> in Alice’s data memories [0], [1]
    data_memo_arr = alice.get_component_by_name(alice.data_memo_arr_name)
    data_memo_arr[0].update_state(psi_b)
    data_memo_arr[1].update_state(psi_c)

    # ONE TeleportApp on Alice; separate apps on receivers
    A = TeleportApp(alice)
    B = TeleportApp(bob)
    C = TeleportApp(charlie)

    # Give the protocol enough time
    start_t1  = 1 * MILLISECOND
    end_t1    = 20 * MILLISECOND
    start_t2  = 1 * MILLISECOND
    end_t2    = 20 * MILLISECOND
    fidelity = 0.1
    mem_size = 1

    # Kick off two concurrent teleports from Alice
    A.start(bob.name,     start_t=start_t1, end_t=end_t1, memory_size=mem_size, fidelity=fidelity, data_memory_index=0)
    A.start(charlie.name, start_t=start_t2, end_t=end_t2, memory_size=mem_size, fidelity=fidelity, data_memory_index=1)

    # Run the simulation
    tl.init()
    tl.run()

    # Results: each item is (timestamp, state)
    assert len(B.results) > 0, "No teleport result recorded at Bob."
    assert len(C.results) > 0, "No teleport result recorded at Charlie."

    out_b = np.array(B.results[0][1])
    out_c = np.array(C.results[0][1])
    return out_b, out_c


def test_dual_teleport_recreates_states():
    """Verify Bob and Charlie each receive their intended state."""
    psi_b = np.array([math.sqrt(3)/2, 0.5])             # to Bob
    psi_c = np.array([1/np.sqrt(5), 2/np.sqrt(5)])      # to Charlie

    out_b, out_c = dual_trial(psi_b, psi_c)

    atol = 1e-6
    assert out_b.shape == psi_b.shape
    assert out_c.shape == psi_c.shape
    assert np.allclose(out_b, psi_b, atol=atol), f"Bob got {out_b} != {psi_b}"
    assert np.allclose(out_c, psi_c, atol=atol), f"Charlie got {out_c} != {psi_c}"

# test_dual_teleport_recreates_states()
# test_teleport_recreates_state()