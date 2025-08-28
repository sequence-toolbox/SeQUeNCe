""" Test for Quantum Teleportation Application
This script tests the quantum teleportation application by simulating a simple two-node network.
It verifies that the teleportation process correctly recreates the original quantum state.
"""
import itertools
import numpy as np
import pytest
from sequence.topology.dqc_net_topo import DQCNetTopo
from sequence.app.teleport_app import TeleportApp
from sequence.constants import MILLISECOND
from sequence.kernel.quantum_utils import verify_same_state_vector



def single_trial(psi, seeds: dict = None):
    """Run a single trial of teleportation with the given quantum state psi.
    Args:       
        psi (np.ndarray): The quantum state to teleport, represented as a numpy array
        seeds (dict): Dictionary of random seeds for the simulation
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
    bsm_nodes = topo.nodes.get(DQCNetTopo.BSM_NODE, [])
    bsm_ab = next((n for n in bsm_nodes if n.name == "BSM_alice_bob"), None)

    # Set random seeds for nodes
    alice.set_seed(seeds["alice"]) 
    bob.set_seed(seeds["bob"]) 
    bsm_ab.set_seed(seeds["BSM_alice_bob"]) 

    # 1) Prepare |ψ> in Alice’s data qubit
    data_memo_arr = alice.get_component_by_name(alice.data_memo_arr_name)
    data_memo_arr[0].update_state(psi)

    # 2) Attach the TeleportApp on both nodes
    A = TeleportApp(alice)
    B = TeleportApp(bob)

    # 3) Kick off teleport
    A.start(
        responder   = bob.name,
        start_t     = 1  * MILLISECOND,
        end_t       = 200 * MILLISECOND,
        memory_size = 1,
        fidelity    = 0.01,
        data_memory_index = 0
    )

    # 4) Run the simulation
    tl.init()
    tl.run()

    # 5) Read out Bob’s data qubit state
    teleported_qubit = B.results[0][1]  # each result is (timestamp, state)
    return np.array(teleported_qubit)

def _random_state(rng: np.random.Generator):
    # Generate a random single-qubit pure state (complex amplitudes) and normalize
    a = rng.normal() + 1j * rng.normal()
    b = rng.normal() + 1j * rng.normal()
    v = np.array([a, b], dtype=complex)
    v = v / np.linalg.norm(v)
    return v


# Prepare 5 random input states and 5 random seed sets (reproducible)
_rng_inputs = np.random.default_rng(12345)
_single_inputs = [_random_state(_rng_inputs) for _ in range(2)]
_single_seeds   = [
    {
        "alice": int(_rng_inputs.integers(0, 2**31-1)),
        "bob": int(_rng_inputs.integers(0, 2**31-1)),
        "BSM_alice_bob": int(_rng_inputs.integers(0, 2**31-1)),
    }
    for _ in range(20)
]


@pytest.mark.parametrize(
    "psi,seeds",
    list(itertools.product(_single_inputs, _single_seeds))
)
def test_teleport_recreates_state(psi, seeds):
    """Test teleportation for 25 cases (5 inputs x 5 seed sets)."""
    out = single_trial(psi, seeds=seeds)

    assert verify_same_state_vector(out, psi), f"teleported state {out} != original {psi}"




"""
Dual-teleport test (3 nodes): Alice teleports to Bob and Charlie concurrently.

We prepare two different states on Alice's data memories:
- data[0] -> (to Bob)
- data[1] -> (to Charlie)

A single TeleportApp is attached to Alice and .start(...) is called twice.
Bob and Charlie each get their own TeleportApp to record results.
"""

def dual_trial(psi_b: np.ndarray, psi_c: np.ndarray, seeds: dict = None):
    """Run a dual-teleport trial on a 3-node network (alice, bob, charlie).
    Args:
        psi_b: state to send to Bob
        psi_c: state to send to Charlie
        seeds (dict): Dictionary of random seeds for the simulation
    Returns:
        (out_b, out_c): teleported states measured at Bob and Charlie
    """
    topo = DQCNetTopo("tests/app/teleport_3node.json")
    tl   = topo.tl

    # import sequence.utils.log as log
    # log_filename = 'tmp/test_teleport.log'
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
    bsm_nodes = topo.nodes.get(DQCNetTopo.BSM_NODE, [])
    bsm_ab = next((n for n in bsm_nodes if n.name == "BSM_alice_bob"), None)
    bsm_ac = next((n for n in bsm_nodes if n.name == "BSM_alice_charlie"), None)

    # Set random seeds for nodes
    alice.set_seed(seeds["alice"]) 
    bob.set_seed(seeds["bob"]) 
    charlie.set_seed(seeds["charlie"]) 
    bsm_ab.set_seed(seeds["BSM_alice_bob"]) 
    bsm_ac.set_seed(seeds["BSM_alice_charlie"]) 

    # Prepare |psi_b> and |psi_c> in Alice’s data memories [0], [1]
    data_memo_arr = alice.get_component_by_name(alice.data_memo_arr_name)
    data_memo_arr[0].update_state(psi_b)
    data_memo_arr[1].update_state(psi_c)

    # ONE TeleportApp on Alice; separate apps on receivers
    A = TeleportApp(alice)
    B = TeleportApp(bob)
    C = TeleportApp(charlie)

    # Give the protocol enough time
    start_t1 = 1 * MILLISECOND
    end_t1   = 200   * MILLISECOND
    start_t2 = 1 * MILLISECOND
    end_t2   = 200   * MILLISECOND
    fidelity = 0.1 # not to activate distillation
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


_dual_inputs = [(_random_state(_rng_inputs), _random_state(_rng_inputs)) for _ in range(2)]
_dual_seeds  = [
    {
        "alice": int(_rng_inputs.integers(0, 2**31-1)),
        "bob": int(_rng_inputs.integers(0, 2**31-1)),
        "charlie": int(_rng_inputs.integers(0, 2**31-1)),
        "BSM_alice_bob": int(_rng_inputs.integers(0, 2**31-1)),
        "BSM_alice_charlie": int(_rng_inputs.integers(0, 2**31-1)),
    }
    for _ in range(20)
]


@pytest.mark.parametrize(
    "psi_b,psi_c,seeds",
    [(*inp, s) for inp, s in itertools.product(_dual_inputs, _dual_seeds)]
)
def test_dual_teleport_recreates_states(psi_b, psi_c, seeds):
    """Verify Bob and Charlie each receive their intended state over 25 cases."""
    out_b, out_c = dual_trial(psi_b, psi_c, seeds=seeds)

    check_bob     = verify_same_state_vector(out_b, psi_b)
    check_charlie = verify_same_state_vector(out_c, psi_c)
    assert check_bob and check_charlie, f"Bob:{check_bob}, got={out_b}, correct={psi_b}. Charlie:{check_charlie}, got={out_c}, correct={psi_c}"
