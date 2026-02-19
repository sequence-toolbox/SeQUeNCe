"""
This provides actions, condition, and request functions for generation, purification, and swapping to be used by the
resource manager.

Action Signature: def action(memories_info: MemoryInfo, args: Arguments) -> ActionReturn

Condition Signature: def condition(memory_info: MemoryInfo, manager: MemoryManager, args: Arguments) -> list[MemoryInfo]

Request Signature: def request(protocols: list[EntanglementProtocol], args: Arguments) -> EntanglementProtocol | None

Actions, Conditions, and Request functions must follow the above signatures. If a function does not use a parameter, it
should prefix the unused parameter with `_`. For example, _manager.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, cast
from ..components.memory import Memory
from ..entanglement_management.entanglement_protocol import EntanglementProtocol
from ..entanglement_management.generation import EntanglementGenerationA
from ..entanglement_management.purification import BBPSSWProtocol
from ..entanglement_management.swapping import (
    EntanglementSwappingA,
    EntanglementSwappingB,
)

if TYPE_CHECKING:
    from ..topology.node import Node
    from .memory_manager import MemoryInfo, MemoryManager

Arguments = dict[str, Any]
RequestFunction = Callable[[list[EntanglementProtocol], Arguments], EntanglementProtocol | None]
ActionReturn = tuple[EntanglementProtocol, list[str | None], list[RequestFunction | None], list[dict[str, Any] | None]]

TempNode = cast("Node", cast(object, None))
TempMemory = cast("Memory", cast(object, None))

# Entanglement Generation Action-Condition-Request
def eg_rule_action1(memories_info: list[MemoryInfo], args: Arguments) -> ActionReturn:
    memories: list[Memory] = [info.memory for info in memories_info]
    memory: Memory = memories[0]
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    protocol = EntanglementGenerationA.create(owner=TempNode,
                                                                    name=f"EGA.{memory.name}",
                                                                    middle=mid,
                                                                    other=path[index - 1],
                                                                    memory=memory)
    return protocol, [None], [None], [None]


def eg_rule_action2(memories_info: list[MemoryInfo], args: Arguments) -> ActionReturn:
    """Action function used by entanglement generation protocol on nodes except the responder, i.e., index < len(path) - 1"""
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA.create(TempNode, "EGA." + memory.name, mid, path[index + 1], memory)
    req_args = {"name": args["name"], "reservation": args["reservation"]}
    return protocol, [path[index + 1]], [eg_req_func], [req_args]


def eg_req_func(protocols: list[EntanglementProtocol], args: Arguments) -> EntanglementGenerationA | None:
    """Function used by `eg_rule_action2` function for selecting generation protocols on the remote node

    Args:
        protocols: the waiting protocols (wait for request)
        args: arguments from the node who sent the request
    Returns:
        the selected protocol
    """
    name = args["name"]
    reservation = args["reservation"]
    for protocol in protocols:
        if isinstance(protocol, EntanglementGenerationA) and protocol.remote_node_name == name and protocol.rule is not None and protocol.rule.get_reservation() == reservation:
            return protocol
    return None


def eg_rule_condition(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by entanglement generation protocol on nodes"""
    memory_indices = args["memory_indices"]
    if memory_info.state == "RAW" and memory_info.index in memory_indices:
        return [memory_info]
    else:
        return []


# Entanglement Purification Action-Condition-Request
def ep_rule_action1(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by BBPSSW protocol on nodes except the responder node"""
    memories = [info.memory for info in memories_info]
    name = f"EP.{memories[0].name}.{memories[1].name}"
    protocol = BBPSSWProtocol.create(TempNode, name, memories[0], memories[1])
    dsts = [memories_info[0].remote_node]
    req_funcs: list[RequestFunction | None] = [ep_req_func1]
    req_args = [{"remote0": memories_info[0].remote_memo, "remote1": memories_info[1].remote_memo}]
    return protocol, dsts, req_funcs, req_args


def ep_rule_action2(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by BBPSSW protocol on nodes except the responder"""
    memories = [info.memory for info in memories_info]
    name = "EP.%s" % memories[0].name
    protocol = BBPSSWProtocol.create(TempNode, name, memories[0], TempMemory)
    return protocol, [None], [None], [None]


def ep_req_func1(protocols: list[EntanglementProtocol], args: Arguments) -> BBPSSWProtocol | None:
    """Function used by `ep_rule_action1` for selecting purification protocols on the remote node
       Will 'combine two BBPSSW into one BBPSSW'

    Args:
        protocols (list): a list of waiting protocols
        args (dict): the arguments
    Returns:
        the selected protocol
    """
    remote0 = args["remote0"]
    remote1 = args["remote1"]

    _protocols = []
    for protocol in protocols:
        if not isinstance(protocol, BBPSSWProtocol):
            continue

        if protocol.kept_memo.name == remote0:
            _protocols.insert(0, protocol)
        if protocol.kept_memo.name == remote1:
            _protocols.insert(1, protocol)

    if len(_protocols) != 2:
        return None

    protocols.remove(_protocols[1])
    _protocols[1].rule.protocols.remove(_protocols[1])
    _protocols[1].kept_memo.detach(_protocols[1])
    _protocols[0].meas_memo = _protocols[1].kept_memo
    _protocols[0].memories = [_protocols[0].kept_memo, _protocols[0].meas_memo]
    _protocols[0].name = _protocols[0].name + "." + _protocols[0].meas_memo.name
    _protocols[0].meas_memo.attach(_protocols[0])

    return _protocols[0]


def ep_rule_condition1(memory_info: MemoryInfo, memory_manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by BBPSSW protocol on nodes except the initiator"""
    memory_indices = args["memory_indices"]
    reservation = args["reservation"]
    purification_mode = args["purification_mode"]

    if purification_mode == "until_target":
        if memory_info.index in memory_indices and memory_info.state in ["ENTANGLED", "PURIFIED"] and memory_info.fidelity < reservation.fidelity:
            for info in memory_manager:
                if info != memory_info and info.index in memory_indices and info.state in ["ENTANGLED", "PURIFIED"] and info.remote_node == memory_info.remote_node and info.fidelity == memory_info.fidelity:
                    assert memory_info.remote_memo != info.remote_memo
                    return [memory_info, info]
    elif purification_mode == "once":
        if memory_info.index in memory_indices and memory_info.state == "ENTANGLED" and memory_info.fidelity < reservation.fidelity:
            for info in memory_manager:
                if info != memory_info and info.index in memory_indices and info.state == "ENTANGLED" and info.remote_node == memory_info.remote_node and info.fidelity == memory_info.fidelity:
                    assert memory_info.remote_memo != info.remote_memo
                    return [memory_info, info]
    return []


def ep_rule_condition2(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by BBPSSW protocol on nodes except the responder"""
    memory_indices = args["memory_indices"]
    fidelity = args["fidelity"]
    purification_mode = args["purification_mode"]

    if purification_mode == "until_target":
        if memory_info.index in memory_indices and memory_info.state in ["ENTANGLED", "PURIFIED"] and memory_info.fidelity < fidelity:
            return [memory_info]
    elif purification_mode == "once":
        if memory_info.index in memory_indices and memory_info.state == "ENTANGLED" and memory_info.fidelity < fidelity:
            return [memory_info]
    return []


# Entanglement Swapping Action-Condition-Request
def es_rule_actionA(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by EntanglementSwappingA protocol on nodes"""
    #es_succ_prob = args["es_succ_prob"]
    #es_degradation = args["es_degradation"]
    memories = [info.memory for info in memories_info]
    protocol = EntanglementSwappingA(
        TempNode,
        f"ESA.{memories[0].name}.{memories[1].name}",
        memories[0],
        memories[1]
    )
    dsts = [info.remote_node for info in memories_info]
    req_funcs: list[RequestFunction | None] = [es_req_func, es_req_func]
    req_args = [{"target_memo": memories_info[0].remote_memo}, {"target_memo": memories_info[1].remote_memo}]
    return protocol, dsts, req_funcs, req_args


def es_rule_actionB(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by EntanglementSwappingB protocol"""
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementSwappingB(TempNode, "ESB." + memory.name, memory)
    return protocol, [None], [None], [None]


def es_req_func(protocols: list[EntanglementProtocol], args: Arguments) -> EntanglementSwappingB | None:
    """Function used by `es_rule_actionA` for selecting swapping protocols on the remote node

    Args:
        protocols (list): a list of waiting protocols
        args (dict): the arguments
    Returns:
        the selected protocol
    """
    target_memo = args["target_memo"]
    for protocol in protocols:
        if isinstance(protocol, EntanglementSwappingB) and protocol.memory.name == target_memo:
            return protocol
    return None


def es_rule_conditionA(memory_info: MemoryInfo, memory_manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by EntanglementSwappingA protocol on nodes"""
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]
    if memory_info.state in ["ENTANGLED", "PURIFIED"] and memory_info.index in memory_indices and memory_info.remote_node == left and memory_info.fidelity >= fidelity:
        for memory_info2 in memory_manager:
            if memory_info2.state in ["ENTANGLED", "PURIFIED"] and memory_info2.index in memory_indices and memory_info2.remote_node == right and memory_info2.fidelity >= fidelity:
                return [memory_info, memory_info2]
    elif memory_info.state in ["ENTANGLED", "PURIFIED"] and memory_info.index in memory_indices and memory_info.remote_node == right and memory_info.fidelity >= fidelity:
        for memory_info2 in memory_manager:
            if memory_info2.state in ["ENTANGLED", "PURIFIED"] and memory_info2.index in memory_indices and memory_info2.remote_node == left and memory_info2.fidelity >= fidelity:
                return [memory_info, memory_info2]
    return []


def es_rule_conditionB1(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by EntanglementSwappingB protocol on nodes of either responder or initiator"""
    memory_indices = args["memory_indices"]
    target_remote = args["target_remote"]  # A - B - C. For A: B is the remote node, C is the target remote
    fidelity = args["fidelity"]
    if memory_info.state in ["ENTANGLED", "PURIFIED"] and memory_info.index in memory_indices and memory_info.remote_node != target_remote and memory_info.fidelity >= fidelity:
        return [memory_info]
    else:
        return []


def es_rule_conditionB2(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by EntanglementSwappingB protocol on intermediate nodes of a path"""
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]
    if memory_info.state in ["ENTANGLED", "PURIFIED"] and memory_info.index in memory_indices and memory_info.remote_node not in [left, right] and memory_info.fidelity >= fidelity:
        return [memory_info]
    else:
        return []
