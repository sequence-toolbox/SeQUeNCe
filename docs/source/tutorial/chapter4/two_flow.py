from typing import List

from sequence.kernel.timeline import Timeline
from sequence.topology.node import BSMNode, Node
from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.entanglement_management.generation import EntanglementGenerationA
from sequence.entanglement_management.purification import BBPSSW
from sequence.entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from sequence.resource_management.resource_manager import ResourceManager
from sequence.resource_management.rule_manager import Rule
from sequence.message import Message
from sequence.resource_management.memory_manager import MemoryInfo, MemoryManager


## Custom Node

class RouterNode(Node):
    def __init__(self, name, tl, memo_size=50):
        super().__init__(name, tl)
        memory_array_name = name + ".MemoryArray"
        memory_array = MemoryArray(memory_array_name, tl, num_memories=memo_size)
        memory_array.add_receiver(self)
        self.add_component(memory_array)

        self.resource_manager = ResourceManager(self, memory_array_name)

    def receive_message(self, src: str, msg: "Message") -> None:
        if msg.receiver == "resource_manager":
            self.resource_manager.received_message(src, msg)
        else:
            if msg.receiver is None:
                matching = [p for p in self.protocols if type(p) == msg.protocol_type]
                for p in matching:
                    p.received_message(src, msg)
            else:
                for protocol in self.protocols:
                    if protocol.name == msg.receiver:
                        protocol.received_message(src, msg)
                        break

    def get_idle_memory(self, info: "MemoryInfo") -> None:
        pass

    def get(self, photon: "Photon", **kwargs):
        dst = kwargs['dst']
        self.send_qubit(dst, photon)


## flow 1

# entanglement generation

def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager", args):
    index_upper = args["index_upper"]
    index_lower = args["index_lower"]
    if memory_info.state == "RAW" \
            and index_lower <= memory_info.index <= index_upper:
        return [memory_info]
    else:
        return []


def eg_req_func(protocols, args):
    remote_node = args["remote_node"]
    index_upper = args["index_upper"]
    index_lower = args["index_lower"]

    for protocol in protocols:
        if not isinstance(protocol, EntanglementGenerationA):
            continue
        mem_arr = protocol.own.get_components_by_type("MemoryArray")[0]
        if protocol.remote_node_name == remote_node and \
                index_lower <= mem_arr.memories.index(protocol.memory) <= index_upper:
            return protocol


def eg_rule_action1(memories_info: List["MemoryInfo"], args):
    mid_name = args["mid_name"]
    other_name = args["other_name"]

    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid_name,
                                       other_name,
                                       memory)
    req_args = {"remote_node": args["node_name"],
                "index_upper": args["index_upper"],
                "index_lower": args["index_lower"]}
    return [protocol, [other_name], [eg_req_func], [req_args]]


def eg_rule_action2(memories_info: List["MemoryInfo"], args):
    mid_name = args["mid_name"]
    other_name = args["other_name"]
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name,
                                       mid_name, other_name, memory)
    return [protocol, [None], [None], [None]]


## flow 2

# entanglement generation

def add_eg_rules(index: int, path: List[RouterNode], middles: List[BSMNode]):
    assert len(path) == len(middles) + 1
    node_names = [node.name for node in path]
    middle_names = [node.name for node in middles]
    node_mems = [[10, 20], [10, 30], [0, 10]]

    node = path[index]
    mem_range = node_mems[index]

    if index > 0:
        action_args = {"mid_name": middle_names[index - 1],
                       "other_name": node_names[index - 1]}
        condition_args = {"index_lower": mem_range[0],
                          "index_upper": mem_range[0] + 9}

        rule = Rule(10, eg_rule_action2, eg_rule_condition, action_args,
                    condition_args)
        node.resource_manager.load(rule)

    if index < (len(path) - 1):
        if index == 0:
            condition_args = {"index_lower": mem_range[0],
                              "index_upper": mem_range[1] - 1}
        else:
            condition_args = {"index_lower": mem_range[1] - 10,
                              "index_upper": mem_range[1] - 1}

        action_args = {"mid_name": middle_names[index],
                       "other_name": node_names[index + 1],
                       "node_name": node.name,
                       "index_upper": node_mems[index + 1][1] - 1,
                       "index_lower": node_mems[index + 1][0]}

        rule = Rule(10, eg_rule_action1, eg_rule_condition, action_args,
                    condition_args)
        node.resource_manager.load(rule)


# entanglement purification

def ep_rule_condition1(memory_info: "MemoryInfo", manager: "MemoryManager",
                       args):
    index_upper = args["index_upper"]
    index_lower = args["index_lower"]
    target_fidelity = args["target_fidelity"]
    if (index_lower <= memory_info.index <= index_upper
            and memory_info.state == "ENTANGLED"
            and memory_info.fidelity < target_fidelity):
        for info in manager:
            if (info != memory_info
                    and index_lower <= info.index <= index_upper
                    and info.state == "ENTANGLED"
                    and info.remote_node == memory_info.remote_node
                    and info.fidelity == memory_info.fidelity):
                assert memory_info.remote_memo != info.remote_memo
                return [memory_info, info]
    return []

def ep_req_func(protocols, args):
    remote1 = args["remote1"]
    remote2 = args["remote2"]

    _protocols = []
    for protocol in protocols:
        if not isinstance(protocol, BBPSSW):
            continue

        if protocol.kept_memo.name == remote1:
            _protocols.insert(0, protocol)
        if protocol.kept_memo.name == remote2:
            _protocols.insert(1, protocol)

    if len(_protocols) != 2:
        return None

    protocols.remove(_protocols[1])
    _protocols[1].rule.protocols.remove(_protocols[1])
    _protocols[1].kept_memo.detach(_protocols[1])
    _protocols[0].meas_memo = _protocols[1].kept_memo
    _protocols[0].memories = [_protocols[0].kept_memo,
                              _protocols[0].meas_memo]
    _protocols[0].name = _protocols[0].name + "." + _protocols[
        0].meas_memo.name
    _protocols[0].meas_memo.attach(_protocols[0])

    return _protocols[0]


def ep_rule_action1(memories_info: List["MemoryInfo"], args):
    memories = [info.memory for info in memories_info]
    name = "EP.%s.%s" % (memories[0].name, memories[1].name)
    protocol = BBPSSW(None, name, memories[0], memories[1])
    dsts = [memories_info[0].remote_node]
    req_funcs = [ep_req_func]
    req_args = {"remote1": memories_info[0].remote_memo,
                "remote2": memories_info[1].remote_memo}
    return [protocol, dsts, req_funcs, [req_args]]


def ep_rule_condition2(memory_info: "MemoryInfo", manager: "MemoryManager",
                       args):
    index_upper = args["index_upper"]
    index_lower = args["index_lower"]
    target_fidelity = args["target_fidelity"]
    if (index_lower <= memory_info.index <= index_upper
            and memory_info.state == "ENTANGLED"
            and memory_info.fidelity < target_fidelity):
        return [memory_info]
    return []


def ep_rule_action2(memories_info: List["MemoryInfo"], args):
    memories = [info.memory for info in memories_info]
    name = "EP.%s" % (memories[0].name)
    protocol = BBPSSW(None, name, memories[0], None)
    return [protocol, [None], [None], [None]]


def add_ep_rules(index: int, path: List[RouterNode], target_fidelity: float):
    node_mems = [[10, 20], [10, 30], [0, 10]]

    node = path[index]
    mem_range = node_mems[index]

    if index > 0:
        condition_args = {"index_lower": mem_range[0],
                          "index_upper": mem_range[1] - 1,
                          "target_fidelity": target_fidelity}

        rule = Rule(10, ep_rule_action1, ep_rule_condition1, {}, condition_args)
        node.resource_manager.load(rule)

    if index < len(path) - 1:
        if index == 0:
            condition_args = {"index_lower": mem_range[0],
                              "index_upper": mem_range[1] - 1,
                              "target_fidelity": target_fidelity}
        else:
            condition_args = {"index_lower": mem_range[1] - 10,
                              "index_upper": mem_range[1] - 1,
                              "target_fidelity": target_fidelity}

        rule = Rule(10, ep_rule_action2, ep_rule_condition2, {}, condition_args)
        node.resource_manager.load(rule)


# entanglement swapping

def es_rule_conditionA(memory_info: "MemoryInfo", manager: "MemoryManager",
                       args):
    index_lower = args["index_lower"]
    index_upper = args["index_upper"]
    target_fidelity = args["target_fidelity"]
    left, right = args["left"], args["right"]

    if (memory_info.state == "ENTANGLED"
            and memory_info.index in range(index_lower, index_upper)
            and memory_info.remote_node == left
            and memory_info.fidelity >= target_fidelity):
        for info in manager:
            if (info.state == "ENTANGLED"
                    and info.index in range(index_lower, index_upper)
                    and info.remote_node == right
                    and info.fidelity >= target_fidelity):
                return [memory_info, info]
    elif (memory_info.state == "ENTANGLED"
          and memory_info.index in range(index_lower, index_upper)
          and memory_info.remote_node == right
          and memory_info.fidelity >= target_fidelity):
        for info in manager:
            if (info.state == "ENTANGLED"
                    and info.index in range(index_lower, index_upper)
                    and info.remote_node == left
                    and info.fidelity >= target_fidelity):
                return [memory_info, info]
    return []


def es_req_func(protocols, args):
    target_memo = args["target_memo"]
    for protocol in protocols:
        if (isinstance(protocol, EntanglementSwappingB)
                and protocol.memory.name == target_memo):
            return protocol


def es_rule_actionA(memories_info: List["MemoryInfo"], args):
    succ_prob = args["succ_prob"]
    degradation = args["degradation"]

    memories = [info.memory for info in memories_info]

    protocol = EntanglementSwappingA(None, "ESA.%s.%s" % (
        memories[0].name, memories[1].name),
                                     memories[0], memories[1],
                                     success_prob=succ_prob,
                                     degradation=degradation)
    dsts = [info.remote_node for info in memories_info]
    req_funcs = [es_req_func, es_req_func]
    req_args = [{"target_memo": memories_info[0].remote_memo},
                {"target_memo": memories_info[1].remote_memo}]
    return [protocol, dsts, req_funcs, req_args]


def es_rule_conditionB(memory_info: "MemoryInfo", manager: "MemoryManager",
                       args):
    index_lower = args["index_lower"]
    index_upper = args["index_upper"]
    target_node = args["target_node"]
    target_fidelity = args["target_fidelity"]

    if (memory_info.state == "ENTANGLED"
            and memory_info.index in range(index_lower, index_upper)
            and memory_info.remote_node != target_node
            and memory_info.fidelity >= target_fidelity):
        return [memory_info]
    else:
        return []


def es_rule_actionB(memories_info: List["MemoryInfo"], args):
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementSwappingB(None, "ESB." + memory.name, memory)
    return [protocol, [None], [None], [None]]


if __name__ == "__main__":
    runtime = 10e12
    tl = Timeline(runtime)

    # nodes
    r1 = RouterNode("r1", tl, memo_size=20)
    r2 = RouterNode("r2", tl, memo_size=30)
    r3 = RouterNode("r3", tl, memo_size=10)

    m12 = BSMNode("m12", tl, ["r1", "r2"])
    m23 = BSMNode("m23", tl, ["r2", "r3"])

    node_list = [r1, r2, r3, m12, m23]
    for i, node in enumerate(node_list):
        node.set_seed(i)

    # create all-to-all classical connections
    cc_delay = 1e9
    for node1 in node_list:
        for node2 in node_list:
            cc = ClassicalChannel("cc_%s_%s" % (node1.name, node2.name), tl,
                                  1e3, delay=cc_delay)
            cc.set_ends(node1, node2.name)

    # create quantum channels linking r1 and r2 to m1
    qc_atten = 0
    qc_dist = 1e3
    qc1 = QuantumChannel("qc_r1_m12", tl, qc_atten, qc_dist)
    qc1.set_ends(r1, m12.name)
    qc2 = QuantumChannel("qc_r2_m12", tl, qc_atten, qc_dist)
    qc2.set_ends(r2, m12.name)
    # create quantum channels linking r2 and r3 to m2
    qc3 = QuantumChannel("qc_r2_m23", tl, qc_atten, qc_dist)
    qc3.set_ends(r2, m23.name)
    qc4 = QuantumChannel("qc_r3_m23", tl, qc_atten, qc_dist)
    qc4.set_ends(r3, m23.name)

    tl.init()

    # load rules for flow 1
    action_args = {"mid_name": "m12", "other_name": "r2", "node_name": "r1",
                   "index_upper": 9, "index_lower": 0}
    condition_args = {"index_lower": 0, "index_upper": 9}
    rule1 = Rule(10, eg_rule_action1, eg_rule_condition, action_args,
                 condition_args)
    r1.resource_manager.load(rule1)
    action_args2 = {"mid_name": "m12", "other_name": "r1"}
    rule2 = Rule(10, eg_rule_action2, eg_rule_condition, action_args2,
                 condition_args)
    r2.resource_manager.load(rule2)

    # load rules for flow 2
    for i in range(3):
        add_eg_rules(i, [r1, r2, r3], [m12, m23])
        add_ep_rules(i, [r1, r2, r3], 0.9)

    condition_args = {"index_lower": 10,
                      "index_upper": 20,
                      "target_node": r3.name,
                      "target_fidelity": 0.9}
    rule = Rule(10, es_rule_actionB, es_rule_conditionB, {}, condition_args)
    r1.resource_manager.load(rule)

    condition_args = {"index_lower": 0,
                      "index_upper": 10,
                      "target_node": r1.name,
                      "target_fidelity": 0.9}
    rule = Rule(10, es_rule_actionB, es_rule_conditionB, {}, condition_args)
    r3.resource_manager.load(rule)

    action_args = {"succ_prob": 1, "degradation": 1}
    condition_args = {"index_lower": 10,
                      "index_upper": 30,
                      "target_fidelity": 0.9,
                      "left": r1.name, "right": r3.name}
    rule = Rule(10, es_rule_actionA, es_rule_conditionA, action_args, condition_args)
    r2.resource_manager.load(rule)

    tl.run()

    print("Router 1 Memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for i, info in enumerate(r1.resource_manager.memory_manager):
        print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                             str(info.fidelity),
                                             str(info.entangle_time * 1e-12)))

    print("Router 2 Memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for i, info in enumerate(r2.resource_manager.memory_manager):
        print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                             str(info.fidelity),
                                             str(info.entangle_time * 1e-12)))

    print("Router 3 Memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for i, info in enumerate(r3.resource_manager.memory_manager):
        print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                             str(info.fidelity),
                                             str(info.entangle_time * 1e-12)))

    print("Rules:")
    for rule in r2.resource_manager.rule_manager.rules:
        print(rule.priority, rule.action)
