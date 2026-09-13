"""Tests for the BSM registry and the physics-ledger hook."""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "example"))

from sequence.components.bsm import BSM, SingleHeraldedBSM, SingleAtomBSM
from sequence.app.request_app import RequestApp
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SINGLE_HERALDED, BARRET_KOK, SECOND
from sequence.entanglement_management.generation import (
    EntanglementGenerationA, EntanglementGenerationB)

from unreliable_midpoint import unreliable_bsm, ledger_protocol  # noqa: F401
from unreliable_midpoint.unreliable_bsm import UnreliableSingleHeraldedBSM
from unreliable_midpoint.run_example import (
    config_with_unreliable_midpoint, TUTORIAL, run)


@pytest.fixture(autouse=True)
def restore_global_types():
    a, b = (EntanglementGenerationA.get_global_type(),
            EntanglementGenerationB.get_global_type())
    yield
    EntanglementGenerationA.set_global_type(a)
    EntanglementGenerationB.set_global_type(b)


def _library(conf, initiator="router_0", responder="router_1"):
    EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    topo = RouterNetTopo(config_source=json.loads(json.dumps(conf)))
    tl = topo.get_timeline()
    apps = {r.name: RequestApp(r)
            for r in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)}
    tl.init()
    apps[initiator].start(responder, 1 * SECOND, int(2.5 * SECOND), 1, 0.8)
    tl.run()
    return apps[initiator].memory_counter, tl


def test_registry_resolution():
    assert BSM.resolve("single_heralded") is SingleHeraldedBSM
    assert BSM.resolve("single_atom") is SingleAtomBSM
    assert BSM.resolve("unreliable_single_heralded") is UnreliableSingleHeraldedBSM
    assert BSM.resolve("no_such_encoding") is None


def test_registered_class_placed_from_config():
    EntanglementGenerationA.set_global_type("ledger_sh")
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    conf = config_with_unreliable_midpoint(p_false_positive=0.5)
    topo = RouterNetTopo(config_source=conf)
    bsm_nodes = topo.nodes[RouterNetTopo.BSM_NODE]
    bsm = bsm_nodes[0].components[bsm_nodes[0].first_component_name]
    assert isinstance(bsm, UnreliableSingleHeraldedBSM)
    assert bsm.p_false_positive == 0.5


def test_ledger_off_equals_library():
    conf = json.load(open(TUTORIAL))
    lib_count, lib_tl = _library(conf)
    EntanglementGenerationA.set_global_type("ledger_sh")
    off_count, off_tl = run(p_false_positive=0.0)
    assert lib_count == off_count == 105
    lib_states = {tuple(sorted(s.keys)): tuple(s.state)
                  for s in lib_tl.quantum_manager.states.values()}
    off_states = {tuple(sorted(s.keys)): tuple(s.state)
                  for s in off_tl.quantum_manager.states.values()}
    assert lib_states == off_states


def test_false_positive_delivers_mixed_pairs():
    # Capture the computed state at delivery: an unbacked pair is written as the
    # maximally mixed state (state[0] == 0.25) while its bookkeeping fidelity
    # stays at the template value 0.9.
    seen = {"mixed": 0, "book": set()}

    class Probe(RequestApp):
        def get_memory(self, info):
            if info.state == "ENTANGLED" and info.index in self.memo_to_reservation:
                r = self.memo_to_reservation[info.index]
                if info.fidelity >= r.fidelity and \
                        info.remote_node in (r.initiator, r.responder):
                    qm = self.node.timeline.quantum_manager
                    k = info.memory.qstate_key
                    if k in qm.states and abs(qm.states[k].state[0] - 0.25) < 1e-9:
                        seen["mixed"] += 1
                        seen["book"].add(round(info.fidelity, 4))
            super().get_memory(info)

    EntanglementGenerationA.set_global_type("ledger_sh")
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    conf = config_with_unreliable_midpoint(p_false_positive=0.5)
    topo = RouterNetTopo(config_source=conf)
    tl = topo.get_timeline()
    apps = {r.name: Probe(r)
            for r in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)}
    tl.init()
    apps["router_0"].start("router_1", 1 * SECOND, int(2.5 * SECOND), 1, 0.8)
    tl.run()
    assert tl.physics_ledger.false_positive > 0
    assert seen["mixed"] > 0            # pairs delivered with computed F = 0.25
    assert seen["book"] == {0.9}        # bookkeeping fidelity unchanged


def test_drop_delivers_none():
    count, tl = run(p_false_positive=0.0, p_drop=1.0)
    assert count == 0
    assert tl.physics_ledger.dropped > 0


def test_run_example_end_to_end():
    count, tl = run(p_false_positive=0.2)
    assert isinstance(count, int)
