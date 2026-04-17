"""
Function definitions for each pre-packaged graph.
Nodes are marked as either processing or switch. Processing nodes are assumed to be either src or dst nodes in
entanglement distribution. Switch nodes are assumed to never be end points.
"""
from itertools import product

import networkx as nx

def build_caveman(cliques: int, size: int) -> nx.Graph:
    """
    Create a caveman topology of l cliques of size k.
    Args:
        cliques: Number of cliques (l)
        size: Size of the cliques (k)

    Returns: Networkx Graph
    """
    G: nx.Graph = nx.connected_caveman_graph(cliques, size)
    for node in G.nodes:
        G.nodes[node]['node_type'] = 'processing'
    return G

def build_grid(size_x: int, size_y: int) -> nx.Graph:
    """
    Create a grid graph
    Args:
        size_x: Nodes on x-axis
        size_y: Nodes on y-axis

    Returns: Networkx graph
    """
    G: nx.Graph = nx.grid_2d_graph(size_x, size_y)
    for node in G.nodes:
        G.nodes[node]["node_type"] = "processing"
    return G

def build_star(outer_nodes: int) -> nx.Graph:
    """
    Create a star graph.
    Args:
        outer_nodes: Number of nodes connected to the center. Center is index 0

    Returns: Networkx Graph
    """
    G: nx.Graph = nx.star_graph(outer_nodes)
    G.nodes[0]["node_type"] = "switch"
    for i in range(1, outer_nodes + 1):
        G.nodes[i]["node_type"] = "processing"
    return G

def build_linear(nodes: int) -> nx.Graph:
    """
    Create a linear graph of size n
    Args:
        nodes: Number of nodes.

    Returns: NetworkX Graph
    """
    G = nx.path_graph(nodes)
    for node in G.nodes:
        G.nodes[node]["node_type"] = "processing"
    return G

def build_mesh(size_x, size_y) -> nx.Graph:
    """
    Create a fully connected grid graph.
    Args:
        size_x: Nodes on x-axis
        size_y: Nodes on y-axis

    Returns: NetworkX Graph
    """
    G = build_grid(size_x, size_y)

    for (x, y) in G.nodes:
        for dx, dy in [(1,1), (1,-1), (-1, 1), (-1, -1)]: # Diagonals from any node with max Deg = 4
            if (x+dx, y+dy) in G.nodes:
                v = (x+dx, y+dy)
                G.add_edge((x, y), v)

    return G

def build_ring(nodes: int) -> nx.Graph:
    """
    Build a cycle/ring graph cycically connected nodes of size n
    Args:
        nodes: Number of nodes in the ring

    Returns: NetworkX Graph

    """

    G: nx.Graph = nx.cycle_graph(nodes)
    for node in G.nodes:
        G.nodes[node]["node_type"] = "processing"
    return G

def build_waxman(nodes, seed=None) -> nx.Graph:
    """
    Builds a random Waxman graph of size n
    Args:
        nodes: Number of nodes
        seed: rng seed

    Returns: NetworkX Graph

    """
    G: nx.Graph = nx.waxman_graph(nodes, seed=seed)
    for node in G.nodes:
        G.nodes[node]["node_type"] = "processing"
    return G

def build_tree(branching_factor: int, nodes: int) -> nx.Graph:
    """
    Create a full r-ary tree of n nodes.
    Args:
        branching_factor: Branching factor in the tree
        nodes: Number of nodes in the tree

    Returns:

    """
    G: nx.Graph = nx.full_rary_tree(branching_factor, nodes)
    for node in G.nodes:
        G.nodes[node]["node_type"] = "processing"
    return G

def build_autonomous_system(nodes: int, seed=None) -> nx.Graph:
    G: nx.Graph = nx.random_internet_as_graph(nodes, seed=seed)
    for node in G.nodes:
        G.nodes[node]["node_type"] = "processing"
    return G

def build_bcube(k: int, n: int) -> nx.Graph:
    """
    C. Guo et al., “BCube: a high performance, server-centric network architecture for modular data centers,”
    SIGCOMM Comput. Commun. Rev., vol. 39, no. 4, pp. 63–74, Aug. 2009, doi: 10.1145/1594977.1592577.
    Args:
        k: Number of levels
        n: Number of BCubes

    Returns: Networkx Graph
    """
    G = nx.Graph()
    assert k >= 1
    assert n >= 1

    # Create the servers addressed by {0,...,n-1}^k+1
    servers: list[tuple] = list(product(range(n), repeat=k + 1))
    G.add_nodes_from(servers, node_type="processing", subset=0)

    # Create the switches addressed by {(l,w): l in [0,...,k], s in {0,...,n-1}^k}
    switches = [(l, s) for l in range(k + 1) for s in product(range(n), repeat=k)]  # noqa: E741
    for l, s in sorted(switches):  # noqa: E741
        G.add_node((l, s), node_type="switch", subset=l + 1)

    for l, s in switches:  # noqa: E741
        for i in range(n):  # There are n-ports on each switch
            index = len(s) - l
            server = s[:index] + (i,) + s[index:]
            G.add_edge((l, s), server)
    return G


def build_k_n(k: int, n: int) -> nx.Graph:
    """
    Create a Fat Tree; k-ary n-tree nx graph parameterized by k and n.
    Contains N=k^n processing nodes and n*k^(n-1) switches

    F. Petrini and M. Vanneschi, “k-ary n-trees: high performance networks for massively parallel architectures,”
    in Proceedings 11th International Parallel Processing Symposium, Apr. 1997, pp. 87–93. doi: 10.1109/IPPS.1997.580853.

    Args:
        k: Number of ports per switch.
        n: Number of levels

    Returns: NetworkX Graph
    """
    G = nx.Graph()

    # Processing Nodes: p for all p in {0,1,...,k-1)^n
    nodes = list(product(range(k), repeat=n))
    G.add_nodes_from(nodes, node_type="processing")
    assert len(nodes) == k**n

    # Switches: (w,l) for all w in {0,1,...,k-1}^(n-1) and l in {0,1,...,n-1}
    switches = [(w, l) for l in range(n) for w in product(range(k), repeat=n - 1)]  # noqa: E741
    G.add_nodes_from(switches, node_type="switch")
    assert len(switches) == n * k ** (n - 1)

    # Create Switch -> Switch edges
    for l in range(n - 1):  # noqa: E741
        for w in product(range(k), repeat=n - 1):
            for w_l in range(k):
                w_prime = list(w)
                w_prime[l] = w_l
                G.add_edge((w, l), (tuple(w_prime), l + 1))

    # Create Switch -> Node edges
    for w in product(range(k), repeat=n - 1):
        for p_last in range(k):
            node = w + (p_last,)
            G.add_edge((w, n - 1), node)
    assert G.number_of_edges() == n * k**n

    return G