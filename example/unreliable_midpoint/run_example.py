"""Run the two-node tutorial config with an unreliable midpoint.

An honest run reproduces the tutorial. With a false-positive rate the midpoint
delivers pairs it did not detect; the ledger protocol writes those as the
maximally mixed state, so their computed fidelity at delivery is 0.25 while the
bookkeeping fidelity stays at the template value and passes the request
threshold.
"""
import json
import os
from sequence.app.request_app import RequestApp
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SINGLE_HERALDED, SECOND
from sequence.entanglement_management.generation import (
    EntanglementGenerationA, EntanglementGenerationB)
from . import unreliable_bsm  # noqa: F401
from . import ledger_protocol  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
TUTORIAL = os.path.join(HERE, "..", "..",
                        "docs/source/tutorial/sequence3min/two_node.json")


def config_with_unreliable_midpoint(p_false_positive=0.0, p_drop=0.0):
    """Load the tutorial config and set its midpoint template to the unreliable
    BSM, selected through the registry.

    Args:
        p_false_positive (float): false-positive rate for the midpoint.
        p_drop (float): drop rate for the midpoint.

    Returns:
        dict: the modified config.
    """
    conf = json.load(open(TUTORIAL))
    # Carry the tutorial's detector settings so the honest path is unchanged;
    # only the encoding and the two rates are added.
    detectors = conf["templates"]["bsm_template"]["SingleHeraldedBSM"]["detectors"]
    conf["templates"]["bsm_template"] = {
        "encoding_type": "unreliable_single_heralded",
        "UnreliableSingleHeraldedBSM": {
            "detectors": detectors,
            "p_false_positive": p_false_positive, "p_drop": p_drop}}
    return conf


def run(p_false_positive=0.0, p_drop=0.0):
    """Run one request and return the delivered count and the ledger.

    Args:
        p_false_positive (float): false-positive rate.
        p_drop (float): drop rate.

    Returns:
        tuple[int, Timeline]: delivered pairs and the timeline (its
            physics_ledger holds the counters).
    """
    EntanglementGenerationA.set_global_type("ledger_sh")
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    conf = config_with_unreliable_midpoint(p_false_positive, p_drop)
    topo = RouterNetTopo(config_source=conf)
    tl = topo.get_timeline()
    apps = {r.name: RequestApp(r)
            for r in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)}
    tl.init()
    apps["router_0"].start("router_1", 1 * SECOND, int(2.5 * SECOND), 1, 0.8)
    tl.run()
    return apps["router_0"].memory_counter, tl


if __name__ == "__main__":
    for p in (0.0, 0.1, 0.5):
        delivered, tl = run(p_false_positive=p)
        print(f"p_false_positive={p}: delivered {delivered}, "
              f"unbacked heralds {tl.physics_ledger.false_positive}")
