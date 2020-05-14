from numpy.random import seed

from sequence.kernel.timeline import Timeline
from sequence.topology.topology import Topology

if __name__ == "__main__":
    # Experiment params and config
    network_config_file = "example/starlight.json"
    runtime = 1e12

    seed(1)
    tl = Timeline(runtime)
    network_topo = Topology("network_topo", tl)
    network_topo.load_config(network_config_file)

    # display components
    #   nodes can be interated from Topology.nodes.values()
    #   quantum channels from Topology.qchannels
    #   classical channels from Topology.cchannels
    print("Nodes:")
    for name, node in network_topo.nodes.items():
        print("\t" + name + ": ", node)
    print("Quantum Channels:")
    for qc in network_topo.qchannels:
        print("\t" + qc.name + ": ", qc)
    print("Classical Channels:")
    for cc in network_topo.cchannels:
        print("\t" + cc.name + ": ", cc)

    routing_tables = {}
    for node in network_topo.nodes:
        routing_tables[node] = network_topo.generate_forwarding_table(node)


