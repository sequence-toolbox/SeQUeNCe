from typing import List, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..resource_management.memory_manager import MemoryInfo, MemoryManager
    from ..entanglement_management.entanglement_protocol import EntanglementProtocol

from ..resource_management.rule_manager import Arguments
from ..entanglement_management.generation import EntanglementGenerationA


def adaptive_eg_rule_condition(memory_info: "MemoryInfo",
                      manager: "MemoryManager",
                      args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by coontinuous entanglement generation protocol on nodes.
    """

    if memory_info.state == "RAW":
        return [memory_info]
    else:
        return []


def adaptive_eg_rule_action(memories_info: List["MemoryInfo"], args: Dict[str, Any]):
    """Action function used by continuous entanglement generation protocol.
    Node should use comparison between local and other names to determine use of rule action 1 or 2.

    Arguments in args:
        local (str): name of local node
        others (str): list of names of other router nodes
        mids (str): list of names of midpoint BSM nodes
        dist (List[float]): probabilities to use for selecting nodes
        rng: random number generator to use (from node)
    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]

    local = args["local"]
    others = args["others"]
    mids = args["mids"]
    dist = args["dist"]
    rng = args["rng"]

    # choose other node
    idx = rng.choice(len(mids), p=dist)
    other = others[idx]
    mid = mids[idx]

    # allocate protocol
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid, other, memory)

    # return
    if local > other:
        req_args = {"name": args["local"]}
        return protocol, [other], [adaptive_eg_req_func], [req_args]
    else:
        return protocol, [None], [None], [None]


def adaptive_eg_req_func(protocols: List["EntanglementProtocol"],
                args: Arguments) -> "EntanglementGenerationA":
    """Function used by `eg_rule_action2` function for selecting generation
    protocols on the remote node

    """
    name = args["name"]
    for protocol in protocols:
        if (isinstance(protocol, EntanglementGenerationA)
                and protocol.remote_node_name == name
                and not protocol.rule.get_reservation()):
            return protocol
