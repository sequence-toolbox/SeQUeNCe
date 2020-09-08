from numpy import random
from typing import List, TYPE_CHECKING

from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.topology.node import BSMNode, Node
from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.entanglement_management.generation import EntanglementGenerationA
from sequence.entanglement_management.purification import BBPSSW
from sequence.entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from sequence.resource_management.resource_manager import ResourceManager
from sequence.resource_management.rule_manager import Rule


## Custom Node

class RouterNode(Node):
    def __init__(self, name, tl, memo_size=50):
        super().__init__(name, tl)
        self.memory_array = MemoryArray(name + ".MemoryArray", tl, num_memories=memo_size)
        self.memory_array.owner = self
        self.resource_manager = ResourceManager(self)

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


## flow 1

# entanglement generation

def eg_rule_condition_f1(memory_info: "MemoryInfo", manager: "MemoryManager"):
    if memory_info.state == "RAW" and memory_info.index < 10:
        return [memory_info]
    else:
        return []

def eg_rule_action_f1_1(memories_info: List["MemoryInfo"]):
    def req_func(protocols):
        for protocol in protocols:
            if isinstance(protocol, EntanglementGenerationA) and protocol.other == "r1" and r2.memory_array.memories.index(protocol.memory) < 10:
                return protocol

    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, "m12", "r2", memory)
    return [protocol, ["r2"], [req_func]]


def eg_rule_action_f1_2(memories_info: List["MemoryInfo"]):
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, "m12", "r1", memory)
    return [protocol, [None], [None]]


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
        def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if memory_info.state == "RAW" and memory_info.index in range(mem_range[0], mem_range[1])[:10]:
                return [memory_info]
            else:
                return []

        def eg_rule_action(memories_info: List["MemoryInfo"]):
            memories = [info.memory for info in memories_info]
            memory = memories[0]
            protocol = EntanglementGenerationA(None, "EGA." + memory.name, middle_names[index - 1], node_names[index - 1], memory)
            return [protocol, [None], [None]]

        rule = Rule(10, eg_rule_action, eg_rule_condition)
        node.resource_manager.load(rule)

    if index < (len(path) - 1):
        if index == 0:
            def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if memory_info.state == "RAW" and memory_info.index in range(mem_range[0], mem_range[1]):
                    return [memory_info]
                else:
                    return []

        else:
            def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if memory_info.state == "RAW" and memory_info.index in range(mem_range[0], mem_range[1])[10:]:
                    return [memory_info]
                else:
                    return []


        def eg_rule_action(memories_info: List["MemoryInfo"]):
            def req_func(protocols):
                for protocol in protocols:
                    if isinstance(protocol, EntanglementGenerationA) and protocol.other == node.name and path[index+1].memory_array.memories.index(protocol.memory) in range(node_mems[index+1][0], node_mems[index+1][1]):
                        return protocol

            memories = [info.memory for info in memories_info]
            memory = memories[0]
            protocol = EntanglementGenerationA(None, "EGA." + memory.name, middle_names[index], node_names[index + 1], memory)
            return [protocol, [node_names[index + 1]], [req_func]]

        rule = Rule(10, eg_rule_action, eg_rule_condition)
        node.resource_manager.load(rule)


# entanglement purification

def add_ep_rules(index: int, path: List[RouterNode], target_fidelity: float):
    node_names = [node.name for node in path]
    node_mems = [[10, 20], [10, 30], [0, 10]]

    node = path[index]
    mem_range = node_mems[index]

    if index > 0:
        def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if (memory_info.index in range(mem_range[0], mem_range[1]) and memory_info.state == "ENTANGLED" and memory_info.fidelity < target_fidelity):
                for info in manager:
                    if (info != memory_info and info.index in range(mem_range[0], mem_range[1])[:10]
                            and info.state == "ENTANGLED" and info.remote_node == memory_info.remote_node
                            and info.fidelity == memory_info.fidelity):
                        assert memory_info.remote_memo != info.remote_memo
                        return [memory_info, info]
            return []

        def ep_rule_action(memories_info: List["MemoryInfo"]):
            memories = [info.memory for info in memories_info]

            def req_func(protocols):
                _protocols = []
                for protocol in protocols:
                    if not isinstance(protocol, BBPSSW):
                        continue

                    if protocol.kept_memo.name == memories_info[0].remote_memo:
                        _protocols.insert(0, protocol)
                    if protocol.kept_memo.name == memories_info[1].remote_memo:
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
                _protocols[0].t0 = _protocols[0].kept_memo.timeline.now()

                return _protocols[0]

            name = "EP.%s.%s" % (memories[0].name, memories[1].name)
            protocol = BBPSSW(None, name, memories[0], memories[1])
            dsts = [memories_info[0].remote_node]
            req_funcs = [req_func]
            return [protocol, dsts, req_funcs]

        rule = Rule(10, ep_rule_action, ep_rule_condition)
        node.resource_manager.load(rule)

    if index < len(path) - 1:
        if index == 0:
            def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if (memory_info.index in range(mem_range[0], mem_range[1])
                        and memory_info.state == "ENTANGLED" and memory_info.fidelity < target_fidelity):
                    return [memory_info]
                return []
        else:
            def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if (memory_info.index in range(mem_range[0], mem_range[1])[10:]
                        and memory_info.state == "ENTANGLED" and memory_info.fidelity < target_fidelity):
                    return [memory_info]
                return []

        def ep_rule_action(memories_info: List["MemoryInfo"]):
            memories = [info.memory for info in memories_info]
            name = "EP.%s" % (memories[0].name)
            protocol = BBPSSW(None, name, memories[0], None)
            return protocol, [None], [None]

        rule = Rule(10, ep_rule_action, ep_rule_condition)
        node.resource_manager.load(rule)


# entanglement swapping 

def add_es_rules(index: int, path: List[RouterNode], target_fidelity: float, succ_prob: float, degradation: float):
    node_names = [node.name for node in path]
    node_mems = [[10, 20], [10, 30], [0, 10]]

    node = path[index]
    mem_range = node_mems[index]

    def es_rule_actionB(memories_info: List["MemoryInfo"]):
        memories = [info.memory for info in memories_info]
        memory = memories[0]
        protocol = EntanglementSwappingB(None, "ESB." + memory.name, memory)
        return [protocol, [None], [None]]

    if index == 0:
        def es_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if (memory_info.state == "ENTANGLED"
                    and memory_info.index in range(mem_range[0], mem_range[1])
                    and memory_info.remote_node != node_names[-1]
                    and memory_info.fidelity >= target_fidelity):
                return [memory_info]
            else:
                return []

        rule = Rule(10, es_rule_actionB, es_rule_condition)
        node.resource_manager.load(rule)

    elif index == len(path) - 1:
        def es_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if (memory_info.state == "ENTANGLED"
                    and memory_info.index in range(mem_range[0], mem_range[1])
                    and memory_info.remote_node != node_names[0]
                    and memory_info.fidelity >= target_fidelity):
                return [memory_info]
            else:
                return []

        rule = Rule(10, es_rule_actionB, es_rule_condition)
        node.resource_manager.load(rule)

    else:
        _path = node_names[:]
        while _path.index(node.name) % 2 == 0:
            new_path = []
            for i, n in enumerate(_path):
                if i % 2 == 0 or i == len(path) - 1:
                    new_path.append(n)
            _path = new_path
        _index = _path.index(node.name)
        left, right = _path[_index - 1], _path[_index + 1]

        def es_rule_conditionA(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if (memory_info.state == "ENTANGLED"
                    and memory_info.index in range(mem_range[0], mem_range[1])
                    and memory_info.remote_node == left
                    and memory_info.fidelity >= target_fidelity):
                for info in manager:
                    if (info.state == "ENTANGLED"
                            and info.index in range(mem_range[0], mem_range[1])
                            and info.remote_node == right
                            and info.fidelity >= target_fidelity):
                        return [memory_info, info]
            elif (memory_info.state == "ENTANGLED"
                  and memory_info.index in range(mem_range[0], mem_range[1])
                  and memory_info.remote_node == right
                  and memory_info.fidelity >= target_fidelity):
                for info in manager:
                    if (info.state == "ENTANGLED"
                            and info.index in range(mem_range[0], mem_range[1])
                            and info.remote_node == left
                            and info.fidelity >= target_fidelity):
                        return [memory_info, info]
            return []

        def es_rule_actionA(memories_info: List["MemoryInfo"]):
            memories = [info.memory for info in memories_info]

            def req_func1(protocols):
                for protocol in protocols:
                    if (isinstance(protocol, EntanglementSwappingB)
                            and protocol.memory.name == memories_info[0].remote_memo):
                        return protocol

            def req_func2(protocols):
                for protocol in protocols:
                    if (isinstance(protocol, EntanglementSwappingB)
                            and protocol.memory.name == memories_info[1].remote_memo):
                        return protocol

            protocol = EntanglementSwappingA(None, "ESA.%s.%s" % (memories[0].name, memories[1].name),
                                             memories[0], memories[1],
                                             success_prob=succ_prob, degradation=degradation)
            dsts = [info.remote_node for info in memories_info]
            req_funcs = [req_func1, req_func2]
            return [protocol, dsts, req_funcs]

        rule = Rule(10, es_rule_actionA, es_rule_conditionA)
        node.resource_manager.load(rule)

        def es_rule_conditionB(memory_info: "MemoryInfo", manager: "MemoryManager") -> List["MemoryInfo"]:
            if (memory_info.state == "ENTANGLED"
                    and memory_info.index in range(mem_range[0], mem_range[1])
                    and memory_info.remote_node not in [left, right]
                    and memory_info.fidelity >= target_fidelity):
                return [memory_info]
            else:
                return []

        rule = Rule(10, es_rule_actionB, es_rule_conditionB)
        node.resource_manager.load(rule)


if __name__ == "__main__":
    random.seed(0)

    runtime = 10e12
    tl = Timeline(runtime)

    # nodes
    r1 = RouterNode("r1", tl, memo_size=20)
    r2 = RouterNode("r2", tl, memo_size=30)
    r3 = RouterNode("r3", tl, memo_size=10)
    
    m12 = BSMNode("m12", tl, ["r1", "r2"])
    m23 = BSMNode("m23", tl, ["r2", "r3"])

    # create all-to-all classical connections
    cc_delay = 1e9
    node_list = [r1, r2, r3, m12, m23]
    for node1 in node_list:
        for node2 in node_list:
            cc = ClassicalChannel("cc_%s_%s"%(node1.name, node2.name), tl, 1e3, delay=cc_delay)
            cc.set_ends(node1, node2)

    # create quantum channels linking r1 and r2 to m1
    qc_atten = 0
    qc_dist = 1e3
    qc1 = QuantumChannel("qc_r1_m12", tl, qc_atten, qc_dist)
    qc1.set_ends(r1, m12)
    qc2 = QuantumChannel("qc_r2_m12", tl, qc_atten, qc_dist)
    qc2.set_ends(r2, m12)
    # create quantum channels linking r2 and r3 to m2
    qc3 = QuantumChannel("qc_r2_m23", tl, qc_atten, qc_dist)
    qc3.set_ends(r2, m23)
    qc4 = QuantumChannel("qc_r3_m23", tl, qc_atten, qc_dist)
    qc4.set_ends(r3, m23)

    tl.init()

    # load rules
    rule1 = Rule(10, eg_rule_action_f1_1, eg_rule_condition_f1)
    r1.resource_manager.load(rule1)
    rule2 = Rule(10, eg_rule_action_f1_2, eg_rule_condition_f1)
    r2.resource_manager.load(rule2)

    for i in range(3):
        add_eg_rules(i, [r1, r2, r3], [m12, m23])
        add_ep_rules(i, [r1, r2, r3], 0.9)
        add_es_rules(i, [r1, r2, r3], 0.9, 1, 1)

    tl.run()

    print("Router 1 Memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for i, info in enumerate(r1.resource_manager.memory_manager):
        print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                             str(info.fidelity), str(info.entangle_time * 1e-12)))

    print("Router 2 Memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for i, info in enumerate(r2.resource_manager.memory_manager):
        print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                             str(info.fidelity), str(info.entangle_time * 1e-12)))

    print("Router 3 Memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for i, info in enumerate(r3.resource_manager.memory_manager):
        print("{:6}\t{:15}\t{:9}\t{}".format(str(i), str(info.remote_node),
                                             str(info.fidelity), str(info.entangle_time * 1e-12)))

    print("Rules:")
    for rule in r2.resource_manager.rule_manager.rules:
        print(rule.priority, rule.action)
