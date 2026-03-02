"""Demo 3 — Config format: before and after.

diff between the legacy flat config format my idea clean
template-based format. Both are still supported since the 
function still supports both formats. tries to detect the
legacy first and then falls into the new format if not.
"""

#BEFORE:

LEGACY_QLAN_CONFIG = {
    "stop_time": 2e12,

    "memo_fidelity_orch":     0.9,
    "memo_frequency_orch":    2000,
    "memo_efficiency_orch":   1,
    "memo_coherence_orch":    -1,
    "memo_wavelength_orch":   500,
    "memo_fidelity_client":   0.9,
    "memo_frequency_client":  2000,
    "memo_efficiency_client": 1,
    "memo_coherence_client":  -1,
    "memo_wavelength_client": 500,

    "local_memories":    2,
    "client_number":     3,
    "measurement_bases": "xx",

    "nodes": [
        {"name": "Orchestrator", "type": "QlanOrchestratorNode", "seed": 0},
        {"name": "client1",      "type": "QlanClientNode",       "seed": 1},
        {"name": "client2",      "type": "QlanClientNode",       "seed": 2},
        {"name": "client3",      "type": "QlanClientNode",       "seed": 3},
    ],
    # ... qconnections, cconnections
}

"""
not bad but it could look more uniform with other formats (like the NetTopo formats)

Adding one new type of node would mean 5 extra keys.
-   more importantly there are only two different kinds of 
    nodes allowed because of the predetermined suffixes. You
    can't have a client 1 and client 2 with different 

"""

# AFTER:

CLEAN_QLAN_CONFIG = {
    "stop_time": 2e12,

    # Structural params only at top level
    "local_memories":    2,
    "client_number":     3,
    "measurement_bases": "xx",

    # Hardware params live in named templates which makes
    # which opens up possibilities for reusable defaults 
    # and easily extendable configs

    "templates": {
        "orch_hw": {
            "MemoryArray": {
                "fidelity":      0.9,
                "frequency":     2000,
                "efficiency":    1,
                "coherence_time": -1,
                "wavelength":    500,
            }
        },
        "client_hw": {
            "MemoryArray": {
                "fidelity":      0.9,
                "frequency":     2000,
                "efficiency":    1,
                "coherence_time": -1,
                "wavelength":    500,
            }
        },
    },

    "nodes": [
        {"name": "Orchestrator", "type": "QlanOrchestratorNode",
         "seed": 0, "template": "orch_hw"},
        {"name": "client1", "type": "QlanClientNode",
         "seed": 1, "template": "client_hw"},
        {"name": "client2", "type": "QlanClientNode",
         "seed": 2, "template": "client_hw"},
        {"name": "client3", "type": "QlanClientNode",
         "seed": 3, "template": "client_hw"},
    ],
    # ... qconnections, cconnections
}


# note: templates are literally just Python dicts so we have consistent
# syntax between configs and actual programs which is cool

# FIRST MOTIVATION: allows configs for qlan and bsm nets to be dealt with using 
# the same kinds of functions, which made it very easy to cut down on logic




####Extra comparison: Chapter 5 tutorial vs templates 
#
# Chapter 5 (docs/source/tutorial/chapter5/star_network.py) sets hardware
# parameters AFTER loading the topology, which the user must define themselves,
# which to me felt a little cumbersome when it could be just as fun as the other parts.
# 
# I don't know how to justify it lol its just nicer
#
# Oh and you can provide those templates to users, or create guis based off of some
# CENTRALIZED templates where users can enter the parameters they want at each node
# and it all outputs cohesively.
#
#
#   def set_parameters(topology):
#       for node in topology.get_nodes_by_type("QuantumRouter"):
#           mem = node.get_components_by_type("MemoryArray")[0]
#           mem.update_memory_params("frequency",      2e3)
#           mem.update_memory_params("coherence_time", 0)
#           mem.update_memory_params("efficiency",     1)
#           mem.update_memory_params("raw_fidelity",   0.93)
#
#       for node in topology.get_nodes_by_type("BSMNode"):
#           bsm = node.get_components_by_type("SingleAtomBSM")[0]
#           bsm.update_detectors_params("efficiency",       0.9)
#           bsm.update_detectors_params("count_rate",       5e7)
#           bsm.update_detectors_params("time_resolution",  100)
#
#       for node in topology.get_nodes_by_type("QuantumRouter"):
#           node.network_manager.protocol_stack[1] \
#               .set_swapping_success_rate(0.90)
#           node.network_manager.protocol_stack[1] \
#               .set_swapping_degradation(0.99)
#
#       for qc in topology.get_qchannels():
#           qc.attenuation = 1e-5
#           qc.frequency   = 1e11
#
#   network_topo = RouterNetTopo("star_network.json")
#   set_parameters(network_topo)   # <-- required every time
#
# Problems:
#   - Users must know the internal component names ("MemoryArray", "SingleAtomBSM")
#   - Users must know the right method on each component type
#   - Hardware params are split across the config file AND this function
#   - Forgetting to call set_parameters gives a silent wrong simulation
#   - Every new experiment needs its own set_parameters variant
#
# With templates, all of this collapses into the config:

STAR_NETWORK_WITH_TEMPLATES = {
    "stop_time": 2e13,
    "templates": {
        "router_hw": {
            "MemoryArray": {
                "frequency":      2000,
                "coherence_time": 0,
                "efficiency":     1,
                "fidelity":       0.93,
            }
        },
        "bsm_hw": {
            "SingleAtomBSM": {
                "efficiency":       0.9,
                "count_rate":       5e7,
                "time_resolution":  100,
            }
        },
    },
    "nodes": [
        {"name": "center", "type": "QuantumRouter", "seed": 0,
         "memo_size": 50, "template": "router_hw"},
        {"name": "end1",   "type": "QuantumRouter", "seed": 1,
         "memo_size": 50, "template": "router_hw"},
        {"name": "end2",   "type": "QuantumRouter", "seed": 2,
         "memo_size": 50, "template": "router_hw"},
    ],
    "qconnections": [
        {"node1": "center", "node2": "end1", "attenuation": 1e-5,
         "distance": 500, "type": "meet_in_the_middle"},
        {"node1": "center", "node2": "end2", "attenuation": 1e-5,
         "distance": 500, "type": "meet_in_the_middle"},
    ],
    "cconnections": [
        {"node1": "center", "node2": "end1", "delay": 5e8},
        {"node1": "center", "node2": "end2", "delay": 5e8},
    ],
}

# Usage:
#   topo = RouterNetTopo("star_network.json")  # or RouterNetTopo(STAR_NETWORK_WITH_TEMPLATES)
#   tl   = topo.get_timeline()
#   tl.init()
#   tl.run()
#
# notice that you can even give the programmer a usable dictionary that looks exactly (almost, some square brackets there)
# that they can plug into RouterNetTopo() and reference back to whenever they want
