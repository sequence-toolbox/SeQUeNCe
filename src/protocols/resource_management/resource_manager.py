from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, List
if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import QuantumRouter
    from .rule_manager import Rule

from ..entanglement_management.entanglement_protocol import EntanglementProtocol
from ..message import Message
from .rule_manager import RuleManager
from .memory_manager import MemoryManager


class ResourceManagerMsgType(Enum):
    REQUEST = auto()
    RESPONSE = auto()
    RELEASE_PROTOCOL = auto()
    RELEASE_MEMORY = auto()


class ResourceManagerMessage(Message):
    """
    Two type of ResourceManagerMessage:
    - REQUEST: request eligible protocols from remote resource manager to pair entanglement protocols
      - ini_protocol: protocol that creates this message
      - request_fun: a function using ResourceManager as input to search eligible protocols on remote node
    - RESPONSE: approve or reject received request
      - is_approved: bool type
      - ini_protocol: protocol that creates REQUEST message
      - paired_protocol: protocol that is paired with ini_protocol
    """

    def __init__(self, msg_type: ResourceManagerMsgType, **kwargs):
        Message.__init__(self, msg_type, "resource_manager")
        self.ini_protocol = kwargs["protocol"]
        if msg_type is ResourceManagerMsgType.REQUEST:
            self.req_condition_func = kwargs["req_condition_func"]
        elif msg_type is ResourceManagerMsgType.RESPONSE:
            self.is_approved = kwargs["is_approved"]
            self.paired_protocol = kwargs["paired_protocol"]
        elif msg_type is ResourceManagerMsgType.RELEASE_PROTOCOL:
            self.protocol = kwargs["protocol"]
        elif msg_type is ResourceManagerMsgType.RELEASE_MEMORY:
            self.memory = kwargs["memory_id"]
        else:
            raise Exception("ResourceManagerMessage gets unknown type of message: %s" % str(msg_type))


class ResourceManager():
    def __init__(self, owner: "QuantumRouter"):
        self.name = "resource_manager"
        self.owner = owner
        self.memory_manager = MemoryManager(owner.memory_array)
        self.memory_manager.set_resource_manager(self)
        self.rule_manager = RuleManager()
        self.rule_manager.set_resource_manager(self)
        # protocols that are requesting remote resource
        self.pending_protocols = []
        # protocols that are waiting request from remote resource
        self.waiting_protocols = []
        self.memory_to_protocol_map = {}

    def load(self, rule: "Rule") -> bool:
        self.rule_manager.load(rule)

        for memory_info in self.memory_manager:
            memories_info = rule.is_valid(memory_info)
            if len(memories_info) > 0:
                rule.do(memories_info)
                for info in memories_info:
                    info.to_occupied()

        return True

    def expire(self, rule: "Rule") -> None:
        created_protocols = self.rule_manager.expire(rule)
        while created_protocols:
            protocol = created_protocols.pop()
            if protocol in self.waiting_protocols:
                self.waiting_protocols.remove(protocol)
            elif protocol in self.pending_protocols:
                self.pending_protocols.remove(protocol)
            elif protocol in self.owner.protocols:
                self.owner.protocols.remove(protocol)
            else:
                raise Exception("Unknown place of protocol")

            for memory in protocol.memories:
                self.update(protocol, memory, "RAW")

    def update(self, protocol: "EntanglementProtocol", memory: "Memory", state: str) -> None:
        self.memory_manager.update(memory, state)
        if protocol:
            memory.remove_protocol(protocol)
            if protocol in protocol.rule.protocols:
                protocol.rule.protocols.remove(protocol)

        if protocol in self.owner.protocols:
            self.owner.protocols.remove(protocol)

        if protocol in self.waiting_protocols:
            self.waiting_protocols.remove(protocol)

        if protocol in self.pending_protocols:
            self.pending_protocols.remove(protocol)

        # check if any rules have been met
        memo_info = self.memory_manager.get_info_by_memory(memory)
        for rule in self.rule_manager:
            memories_info = rule.is_valid(memo_info)
            if len(memories_info) > 0:
                rule.do(memories_info)
                for info in memories_info:
                    info.to_occupied()
                return

        self.owner.get_idle_memory(memo_info)

    def get_memory_manager(self):
        return self.memory_manager

    def send_request(self, protocol: "EntanglementProtocol", req_dst: str,
                     req_condition_func: Callable[[List["EntanglementProtocol"]], "EntanglementProtocol"]):
        protocol.own = self.owner
        if req_dst is None:
            self.waiting_protocols.append(protocol)
            return
        if not protocol in self.pending_protocols:
            self.pending_protocols.append(protocol)
        msg = ResourceManagerMessage(ResourceManagerMsgType.REQUEST, protocol=protocol,
                                     req_condition_func=req_condition_func)
        self.owner.send_message(req_dst, msg)

    def received_message(self, src: str, msg: "ResourceManagerMessage") -> None:
        if msg.msg_type is ResourceManagerMsgType.REQUEST:
            protocol = msg.req_condition_func(self.waiting_protocols)
            if protocol is not None:
                protocol.set_others(msg.ini_protocol)
                new_msg = ResourceManagerMessage(ResourceManagerMsgType.RESPONSE, protocol=msg.ini_protocol,
                                                 is_approved=True, paired_protocol=protocol)
                self.owner.send_message(src, new_msg)
                self.waiting_protocols.remove(protocol)
                self.owner.protocols.append(protocol)
                protocol.start()
                return

            new_msg = ResourceManagerMessage(ResourceManagerMsgType.RESPONSE, protocol=msg.ini_protocol,
                                             is_approved=False, paired_protocol=None)
            self.owner.send_message(src, new_msg)
        elif msg.msg_type is ResourceManagerMsgType.RESPONSE:
            protocol = msg.ini_protocol

            if protocol not in self.pending_protocols:
                if msg.is_approved:
                    self.release_remote_protocol(src, msg.paired_protocol)
                return

            if msg.is_approved:
                protocol.set_others(msg.paired_protocol)
                if protocol.is_ready():
                    self.pending_protocols.remove(protocol)
                    self.owner.protocols.append(protocol)
                    protocol.own = self.owner
                    protocol.start()
            else:
                protocol.rule.protocols.remove(protocol)
                for memory in protocol.memories:
                    memory.remove_protocol(protocol)
                    info = self.memory_manager.get_info_by_memory(memory)
                    if info.remote_node is None:
                        self.update(None, memory, "RAW")
                    else:
                        self.update(None, memory, "ENTANGLED")
                self.pending_protocols.remove(protocol)
        elif msg.msg_type is ResourceManagerMsgType.RELEASE_PROTOCOL:
            if msg.protocol in self.owner.protocols:
                assert isinstance(msg.protocol, EntanglementProtocol)
                msg.protocol.release()
        elif msg.msg_type is ResourceManagerMsgType.RELEASE_MEMORY:
            target_id = msg.memory
            for protocol in self.owner.protocols:
                for memory in protocol.memories:
                    if memory.name == target_id:
                        protocol.release()
                        return

    def memory_expire(self, memory: "Memory"):
        self.update(None, memory, "RAW")

    def release_remote_protocol(self, dst: str, protocol: "EntanglementProtocol") -> None:
        msg = ResourceManagerMessage(ResourceManagerMsgType.RELEASE_PROTOCOL, protocol=protocol)
        self.owner.send_message(dst, msg)

    def release_remote_memory(self, init_protocol: "EntanglementProtocol", dst: str, memory_id: str) -> None:
        msg = ResourceManagerMessage(ResourceManagerMsgType.RELEASE_MEMORY, protocol=init_protocol, memory_id=memory_id)
        self.owner.send_message(dst, msg)
