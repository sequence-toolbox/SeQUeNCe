"""
This provides actions, condition, and request functions for generation, purification, and swapping to be used by the
resource manager.

Action Signature: def action(memories_info: MemoryInfo, args: Arguments) -> ActionReturn

Condition Signature: def condition(memory_info: MemoryInfo, manager: MemoryManager, args: Arguments) -> list[MemoryInfo]

Request Signature: def request(protocols: list[EntanglementProtocol], args: Arguments) -> EntanglementProtocol | None

Actions, Conditions, and Request functions must follow the above signatures. If a function does not use a parameter, it
should prefix the unused parameter with `_`. For example, _manager.

Example:






"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, cast
from ..components.memory import Memory
from ..entanglement_management.entanglement_protocol import EntanglementProtocol
from ..entanglement_management.generation import EntanglementGenerationA
from ..entanglement_management.purification import BBPSSWProtocol
from ..entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB

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
    """Action function used by entanglement generation protocol on the responder node, i.e., index = len(path) - 1
    
    Args:
        memories_info: the list of memory info that satisfy the condition function
        args: the arguments defined in the rule, should contain "mid", "path", and "index"

    Returns:
        ActionReturn: the protocol to be executed, None, None, None 
                      (this protocol does not send Resource Manager request, but wait for the request from the other node)
    """
    memories: list[Memory] = [info.memory for info in memories_info]
    memory: Memory = memories[0]
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    protocol = EntanglementGenerationA.create(owner=TempNode, name=f"EGA.{memory.name}",
                                              middle=mid, other=path[index - 1], memory=memory)
    return protocol, [None], [None], [None]


def eg_rule_action2(memories_info: list[MemoryInfo], args: Arguments) -> ActionReturn:
    """Action function used by entanglement generation protocol on nodes except the responder, i.e., index < len(path) - 1
    
    Args:
        memories_info: the list of memory info that satisfy the condition function
        args: the arguments defined in the rule, should contain "mid", "path", and "index"

    Returns:
        ActionReturn: the protocol to be executed, the destination of the request, 
                      the request function, and the arguments for request function
    """
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA.create(TempNode, "EGA." + memory.name, mid, path[index + 1], memory)
    req_args = {"name": args["name"], "reservation": args["reservation"]}
    return protocol, [path[index + 1]], [eg_req_func], [req_args]


def eg_rule_condition(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by entanglement generation protocol on nodes
    
    Args:
        memory_info: the memory info to be checked
        _manager: the memory manager (not used in this condition function)
        args: the arguments defined in the rule
    Returns:
        list[MemoryInfo]: the list of memory info that satisfy the condition
    """
    memory_indices = args["memory_indices"]
    if memory_info.state == "RAW" and memory_info.index in memory_indices:
        return [memory_info]
    else:
        return []


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
        # Select correct EntanglementGenerationA protocol.
        if (isinstance(protocol, EntanglementGenerationA)
                and protocol.remote_node_name == name
                and protocol.rule is not None
                and protocol.rule.get_reservation() == reservation):
            return protocol
    return None


# Entanglement Purification Action-Condition-Request
def ep_rule_action1(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by BBPSSW protocol on nodes except the responder node
    
    Args:
        memories_info: the list of memory info that satisfy the condition function
        _args: the arguments defined in the rule (not used in this action function)

    Returns:
        ActionReturn: the protocol to be executed, the destination of the request, 
                      the request function, and the arguments for request function
    """
    memories = [info.memory for info in memories_info]
    name = f"EP.{memories[0].name}.{memories[1].name}"
    protocol = BBPSSWProtocol.create(TempNode, name, memories[0], memories[1])
    dsts = [memories_info[0].remote_node]
    req_funcs: list[RequestFunction | None] = [ep_req_func1]
    req_args = [{"remote0": memories_info[0].remote_memo, "remote1": memories_info[1].remote_memo}]
    return protocol, dsts, req_funcs, req_args


def ep_rule_action2(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by BBPSSW protocol on nodes except the responder
    
    Args:
        memories_info: the list of memory info that satisfy the condition function
        _args: the arguments defined in the rule (not used in this action function)

    Returns:
        ActionReturn: the protocol to be executed, None, None, None
                      (this protocol does not send Resource Manager request, but wait for the request from the other node)
    """
    memories = [info.memory for info in memories_info]
    name = "EP.%s" % memories[0].name
    protocol = BBPSSWProtocol.create(TempNode, name, memories[0], TempMemory)
    return protocol, [None], [None], [None]


def ep_rule_condition1(kept_memory: MemoryInfo, memory_manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """
    Condition function used by BBPSSW protocol on nodes except the initiator (everything in the path after the initiator)
    Args:
        kept_memory: the memory info to be checked
        memory_manager: the memory manager to get other memory info
        args: the arguments defined in a rule should contain "memory_indices", "fidelity", and "purification_mode"

    Returns:
        list[MemoryInfo]: a list of two the memory info (memory_info, memory_info2) that satisfy the condition
    """
    memory_indices = args["memory_indices"]
    reservation = args["reservation"]
    purification_mode = args["purification_mode"]

    if purification_mode == "until_target":
        # the first memory is the kept memory during purification
        if (kept_memory.index in memory_indices
                                 and kept_memory.state in ["ENTANGLED", "PURIFIED"]
                                 and kept_memory.fidelity < reservation.fidelity):
            for measured_memory in memory_manager:
                # Purification requires kept and measured memory,
                if (measured_memory != kept_memory
                      and measured_memory.index in memory_indices
                      and measured_memory.state in ["ENTANGLED", "PURIFIED"]
                      and measured_memory.remote_node == kept_memory.remote_node
                      and measured_memory.fidelity == kept_memory.fidelity):
                    assert kept_memory.remote_memo != measured_memory.remote_memo
                    return [kept_memory, measured_memory]

    elif purification_mode == "once":
        # the first memory is the kept memory during purification
        if (kept_memory.index in memory_indices
             and kept_memory.state == "ENTANGLED"
             and kept_memory.fidelity < reservation.fidelity):
            for measured_memory in memory_manager:
                # the second memory is the measured memory during purification
                if (measured_memory != kept_memory
                      and measured_memory.index in memory_indices
                      and measured_memory.state == "ENTANGLED"
                      and measured_memory.remote_node == kept_memory.remote_node
                      and measured_memory.fidelity == kept_memory.fidelity):
                    assert kept_memory.remote_memo != measured_memory.remote_memo
                    return [kept_memory, measured_memory]

    return []


def ep_rule_condition2(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by BBPSSW protocol on nodes except the responder

    Args:
        memory_info: the memory info to be checked
        manager: the memory manager to get other memory info (not used in this condition function)
        args: the arguments defined in the rule should contain "memory_indices", "fidelity", and "purification_mode"

    Returns:
        list[MemoryInfo]: the list of memory info that satisfy the condition
    """
    memory_indices = args["memory_indices"]
    fidelity = args["fidelity"]
    purification_mode = args["purification_mode"]

    if purification_mode == "until_target":
        if  (memory_info.index in memory_indices
                 and memory_info.state in ["ENTANGLED", "PURIFIED"]
                 and memory_info.fidelity < fidelity):
            return [memory_info]

    elif purification_mode == "once":
        if (memory_info.index in memory_indices
             and memory_info.state == "ENTANGLED"
             and memory_info.fidelity < fidelity):
            return [memory_info]

    return []


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


# Entanglement Swapping Action-Condition-Request
def es_rule_actionA(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by EntanglementSwappingA protocol on nodes
    
    Args:
        memories_info: a list of memory info
        _args: the arguments defined in the rule (not used in this action function)
    
    Returns:
        ActionReturn: the protocol to be executed, the destination of the request, 
                      the request function, and the arguments for request function
    """
    # TODO: add es_succ_prob and es_degradation into arguments
    #es_succ_prob = args["es_succ_prob"]
    #es_degradation = args["es_degradation"]
    memories = [info.memory for info in memories_info]
    protocol = EntanglementSwappingA(TempNode, f"ESA.{memories[0].name}.{memories[1].name}", memories[0], memories[1])
    dsts = [info.remote_node for info in memories_info]
    req_funcs: list[RequestFunction | None] = [es_req_func, es_req_func]
    req_args = [{"target_memo": memories_info[0].remote_memo}, {"target_memo": memories_info[1].remote_memo}]
    return protocol, dsts, req_funcs, req_args


def es_rule_actionB(memories_info: list[MemoryInfo], _args: Arguments) -> ActionReturn:
    """Action function used by EntanglementSwappingB protocol
    
    Args:
        memories_info: a list of memory info
        _args: the arguments defined in the rule (not used in this action function)
    
    Returns:
        ActionReturn: the protocol to be executed, None, None, None
                      (this protocol does not send Resource Manager request, but wait for the request from the other node)
    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementSwappingB(TempNode, "ESB." + memory.name, memory)
    return protocol, [None], [None], [None]


def es_rule_conditionA(memory_info: MemoryInfo, memory_manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by EntanglementSwappingA protocol on nodes
    
    Args:
        memory_info: the memory info to be checked
        memory_manager: the memory manager to get other memory info
        args: the arguments defined in the rule, should contain "memory_indices", "left", "right", and "fidelity"
    
    Returns:
        list[MemoryInfo]: a list of two memory info (memory_info, memory_info2) that satisfy the condition
    """
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]

    # case 1: memory_info is the "right hand side" memory
    # the first memory is the "right hand side" memory during swapping
    if (memory_info.state in ["ENTANGLED", "PURIFIED"]
         and memory_info.index in memory_indices
         and memory_info.remote_node == left
         and memory_info.fidelity >= fidelity):
        for memory_info2 in memory_manager:
            # the second memory is the "left hand side" memory during swapping
            if (memory_info2.state in ["ENTANGLED", "PURIFIED"]
                  and memory_info2.index in memory_indices
                  and memory_info2.remote_node == right
                  and memory_info2.fidelity >= fidelity):
                return [memory_info, memory_info2]
    
    # case 2: memory_info is the "left hand side" memory
    # the first memory is the "left hand side" memory during swapping
    if (memory_info.state in ["ENTANGLED", "PURIFIED"]
            and memory_info.index in memory_indices
            and memory_info.remote_node == right
            and memory_info.fidelity >= fidelity):
        for memory_info2 in memory_manager:
            # the second memory is the "right hand side" memory during swapping
            if (memory_info2.state in ["ENTANGLED", "PURIFIED"]
                  and memory_info2.index in memory_indices
                  and memory_info2.remote_node == left
                  and memory_info2.fidelity >= fidelity):
                return [memory_info, memory_info2]
    
    return []


def es_rule_conditionB1(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by EntanglementSwappingB protocol on nodes of either responder or initiator
    
    Args:
        memory_info: the memory info to be checked
        _manager: the memory manager to get other memory info (not used in this condition function)
        args: the arguments defined in the rule, should contain "memory_indices", "target_remote", and "fidelity"

    Returns:
        list[MemoryInfo]: the list of memory info that satisfy the condition
    """
    memory_indices = args["memory_indices"]
    target_remote = args["target_remote"]  # A - B - C. For A: B is the remote node, C is the target remote
    fidelity = args["fidelity"]
    if (memory_info.state in ["ENTANGLED", "PURIFIED"]
                             and memory_info.index in memory_indices
                             and memory_info.remote_node != target_remote
                             and memory_info.fidelity >= fidelity):
        return [memory_info]
    else:
        return []


def es_rule_conditionB2(memory_info: MemoryInfo, _manager: MemoryManager, args: Arguments) -> list[MemoryInfo]:
    """Condition function used by EntanglementSwappingB protocol on intermediate nodes of a path
    
    Args:
        memory_info: the memory info to be checked
        _manager: the memory manager to get other memory info (not used in this condition function)
        args: the arguments defined in the rule, should contain "memory_indices", "left", "right", and "fidelity"
    
    Returns:
        list[MemoryInfo]: the list of memory info that satisfy the condition
    """
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]
    if (memory_info.state in ["ENTANGLED", "PURIFIED"]
                             and memory_info.index in memory_indices
                             and memory_info.remote_node not in [left, right]
                             and memory_info.fidelity >= fidelity):
        return [memory_info]
    else:
        return []


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
