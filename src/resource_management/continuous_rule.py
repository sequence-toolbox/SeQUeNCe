from typing import List, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..resource_management.memory_manager import MemoryInfo, MemoryManager
    from ..entanglement_management.entanglement_protocol import EntanglementProtocol

from ..resource_management.rule_manager import Arguments
from ..entanglement_management.generation import EntanglementGenerationA


def eg_rule_condition(memory_info: "MemoryInfo",
                      manager: "MemoryManager",
                      args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by coontinuous entanglement generation protocol on nodes.
    """

    if memory_info.state == "RAW":
        return [memory_info]
    else:
        return []


def eg_rule_action1(memories_info: List["MemoryInfo"], args: Dict[str, Any]):
    """Action function used by continuous entanglement generation protocol.
    Node should use comparison between local and other names to determine use of rule action 1 or 2.

    Arguments in args:
        mid (str): name of midpoint BSM node
        other (str): name of other router node
    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    mid = args["mid"]
    other = args["other"]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid,
                                       other, memory)
    return protocol, [None], [None], [None]


def eg_req_func(protocols: List["EntanglementProtocol"],
                args: Arguments) -> "EntanglementGenerationA":
    """Function used by `eg_rule_action2` function for selecting generation
    protocols on the remote node

    """
    # TODO: check if protocol not for reservation
    name = args["name"]
    for protocol in protocols:
        if (isinstance(protocol, EntanglementGenerationA)
                and protocol.remote_node_name == name
                and not protocol.rule.get_reservation()):
            return protocol


def eg_rule_action2(memories_info: List["MemoryInfo"], args: Arguments):
    """Action function used by continuous entanglement generation protocol.
    Node should use comparison between local and other names to determine use of rule action 1 or 2.

    Arguments in args:
        mid (str): name of midpoint BSM node
        other (str): name of other router node
    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    mid = args["mid"]
    other = args["other"]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid,
                                       other, memory)
    req_args = {"name": args["name"]}
    return protocol, [other], [eg_req_func], [req_args]
