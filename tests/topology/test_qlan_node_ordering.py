"""Tests for QlanNetworkImpl._ordered_node_dicts edge cases.

The orchestrator constructor requires len(local_memories) == len(remote_memories) - 1.
Remote memories are populated client-by-client during construction, so the orchestrator
MUST be constructed after all clients. _ordered_node_dicts enforces this regardless
of the order nodes appear in the config.
"""

import pytest

from sequence.topology.qlan_star_topo import QlanStarTopo
from sequence.topology.const_topo import ORCHESTRATOR, CLIENT


# Shared legacy-format memory params for all tests
_MEM = dict(
    memo_fidelity_orch=0.9,   memo_frequency_orch=2000,
    memo_efficiency_orch=1,   memo_coherence_orch=-1,   memo_wavelength_orch=500,
    memo_fidelity_client=0.9, memo_frequency_client=2000,
    memo_efficiency_client=1, memo_coherence_client=-1, memo_wavelength_client=500,
)

_ORCH = {"name": "orch", "type": "QlanOrchestratorNode", "seed": 0}
_C1   = {"name": "c1",   "type": "QlanClientNode",       "seed": 1}
_C2   = {"name": "c2",   "type": "QlanClientNode",       "seed": 2}


def _make(nodes, local_memories=1, measurement_bases="z", client_number=2):
    return QlanStarTopo(
        {"nodes": nodes, "stop_time": 1e12},
        local_memories=local_memories,
        client_number=client_number,
        measurement_bases=measurement_bases,
        **_MEM,
    )


def test_ordering_orch_listed_first():
    """Orchestrator before clients in config — reordering saves it."""
    topo = _make([_ORCH, _C1, _C2])
    assert len(topo.get_nodes_by_type(ORCHESTRATOR)) == 1
    assert len(topo.get_nodes_by_type(CLIENT)) == 2


def test_ordering_clients_listed_first():
    """Clients before orchestrator — should also work (sort is idempotent)."""
    topo = _make([_C1, _C2, _ORCH])
    assert len(topo.get_nodes_by_type(ORCHESTRATOR)) == 1
    assert len(topo.get_nodes_by_type(CLIENT)) == 2


def test_zero_clients_raises():
    """No clients means orchestrator gets empty remote_memories — constructor raises."""
    with pytest.raises(ValueError):
        _make([_ORCH], client_number=0)


def test_client_count_mismatch_raises():
    """local_memories=2 requires 3 clients, but only 2 provided — constructor raises."""
    with pytest.raises(ValueError):
        _make([_ORCH, _C1, _C2], local_memories=2, measurement_bases="zz", client_number=2)
