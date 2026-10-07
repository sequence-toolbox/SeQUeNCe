"""
Classical delay utility functions.
"""

from networkx import Graph, single_source_dijkstra, exception
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SPEED_OF_LIGHT, MICROSECOND


def classical_delay(distance: float, hop_count: int, classical_delay_node: float, classical_delay_hop: float) -> int:
    """Model the classical delay as a function of distance and hop count

    Args:
        distance (float): the distance between source and destination in km
        hop_count (int): the number of hops/nodes between source and destination
        classical_delay_node (float): delay at the destination node in microseconds
        classical_delay_hop (float): delay for each intermediate hop in microseconds
    
    Returns:
        int: the delay in picoseconds
    """
    return int(distance / SPEED_OF_LIGHT + (hop_count * classical_delay_hop + classical_delay_node) * MICROSECOND)


def update_cchannel_delay(topo: RouterNetTopo, classical_delay_node: float, classical_delay_hop: float) -> None:
    """Update the delay of classical channels based on the network topology and classical delay model.

    Args:
        topo (RouterNetTopo): the topology of the network
        classical_delay_node (float): delay at the destination node in microseconds
        classical_delay_hop (float): delay for each intermediate hop in microseconds
    """
    nodes = [node.name for node in topo.nodes[topo.QUANTUM_ROUTER]]
    graph = Graph()
    for node in nodes:
        graph.add_node(node)

    all_paths = {}  # (src, dst) -> (length: float, hop: int, path: tuple)
    costs = {}      # the cost of each edge in the graph, used for Dijkstra's algorithm
    # process the classical channels within a link: node -- BSM -- node
    for qc in topo.qchannels:
        router = qc.sender.name
        bsm = qc.receiver
        all_paths[(router, bsm)] = (qc.distance, 0, (router, bsm))
        all_paths[(bsm, router)] = (qc.distance, 0, (bsm, router))

        if bsm not in costs:
            costs[bsm] = [router, qc.distance]
        else:
            costs[bsm] = [router] + costs[bsm]
            costs[bsm][-1] += qc.distance

    # process the classical channels between nodes: node -- node
    graph.add_weighted_edges_from(costs.values())
    for src in nodes:
        for dst in nodes:
            if src == dst:
                continue
            try:
                if dst > src:
                    length, path = single_source_dijkstra(graph, src, dst)
                else:
                    length, path = single_source_dijkstra(graph, dst, src)
                    path = path[::-1]
                hop_count = len(path) - 2
                all_paths[(src, dst)] = (length, hop_count, tuple(path))
            except exception.NetworkXNoPath:
                all_paths[(src, dst)] = (float('inf'), 0, ())

    # update the classical channel delay
    for cc in topo.cchannels:
        src = cc.sender.name
        dst = cc.receiver
        length, hop_count, path = all_paths[(src, dst)]
        if length == float('inf'):
            cc.delay = topo.get_timeline().stop_time + 1
            cc.distance = float('inf')
        else:
            cc.delay = classical_delay(length, hop_count, classical_delay_node, classical_delay_hop)
            cc.distance = length
