"""Definition of resource managemer.

This module defines the resource manager, which composes the SeQUeNCe resource management module.
The manager uses a memories manager and rule manager to track memories and control entanglement operations, respectively.
This module also defines the message type used by the resource manager.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from ..components.memories import Memory
    from ..topology.node import QuantumRouter
    from .rule_manager import Rule, Arguments

from ..entanglement_management.entanglement_protocol import EntanglementProtocol
from ..message import Message
from ..utils import log
from .rule_manager import RuleManager
from .memory_manager import MemoryManager, MemoryInfo


RequestConditionFunc = Callable[[list["EntanglementProtocol"]], "EntanglementProtocol"]


class ResourceManagerMsgType(Enum):
    """Available message types for the ResourceManagerMessage."""

    REQUEST = auto()
    RESPONSE = auto()
    RELEASE_PROTOCOL = auto()
    RELEASE_MEMORY = auto()


class ResourceManagerMessage(Message):
    """Message for resource manager communication.

    There are four types of ResourceManagerMessage:

    * REQUEST: request eligible protocols from remote resource manager to pair entanglement protocols.
    * RESPONSE: approve or reject received request.
    * RELEASE_PROTOCOL: release the protocol on the remote node
    * RELEASE_MEMORY: release the memories on the remote node

    Attributes:
        ini_protocol_name (str): name of protocol that creates the original REQUEST message.
        ini_node_name (str): name of the node that creates the original REQUEST message.
        ini_memories_name (str): name of the memories.
        string (str): for __str__() purpose.
        request_fun (func): a function using ResourceManager to search eligible protocols on remote node (if `msg_type` == REQUEST).
        is_approved (bool): acceptance/failure of condition function (if `msg_type` == RESPONSE).
        paired_protocol (str): protocol that is paired with ini_protocol (if `msg-type` == RESPONSE).
    """

    def __init__(self, msg_type: ResourceManagerMsgType, **kwargs):
        super().__init__(msg_type, "resource_manager")
        self.ini_protocol_name = kwargs["protocol"]
        self.ini_node_name = kwargs["node"]
        self.ini_memories_name = kwargs["memories"]
        self.string = "type={}, ini_protocol_name={}, ini_node_name={}, ini_memories_name={}".format(
                       msg_type.name, self.ini_protocol_name, self.ini_node_name, self.ini_memories_name)

        if msg_type is ResourceManagerMsgType.REQUEST:
            self.req_condition_func = kwargs["req_condition_func"]
            self.req_args = kwargs["req_args"]
            self.string += ", req_condition_func={}, req_args={}".format(self.req_condition_func, self.req_args)
        elif msg_type is ResourceManagerMsgType.RESPONSE:
            self.is_approved = kwargs["is_approved"]
            self.paired_protocol = kwargs["paired_protocol"]
            self.paired_node = kwargs["paired_node"]
            self.paired_memories = kwargs["paired_memories"]
            self.string += ", is_approved={}, paired_protocol={}, paired_node={}, paired_memories={}".format(
                            self.is_approved, self.paired_protocol, self.paired_node, self.paired_memories)
        elif msg_type is ResourceManagerMsgType.RELEASE_PROTOCOL:
            self.protocol = kwargs["protocol"]
            self.string += ", release_protocol={}".format(self.protocol)
        elif msg_type is ResourceManagerMsgType.RELEASE_MEMORY:
            self.memory = kwargs["memory_id"]
            self.string += ", release_memory={}".format(self.memory)
        else:
            raise Exception("ResourceManagerMessage gets unknown type of message: {}".format(str(msg_type)))

    def __str__(self) -> str:
        return self.string


class ResourceManager:
    """Class to define the resource manager.

    The resource manager uses a memories manager to track memories states for the entanglement protocols.
    It also uses a rule manager to direct the creation and operation of entanglement protocols.

    Attributes:
        name (str): label for manager instance.
        owner (QuantumRouter): node that resource manager is attached to.
        memory_manager (MemoryManager): internal memories manager object.
        rule_manager (RuleManager): internal rule manager object.
        pending_protocols (list[Protocol]): list of protocols awaiting a response for a remote resource request.
        waiting_protocols (list[Protocol]): list of protocols awaiting a request from a remote protocol.
    """

    def __init__(self, owner: "QuantumRouter", memory_array_name: str):
        """Constructor for resource manager.
        
        Args:
            owner (QuantumRouter): node to attach to.
        """

        self.name = f"{owner.name}.resource_manager"
        self.owner = owner
        self.memory_manager = MemoryManager(owner.components[memory_array_name])
        self.memory_manager.set_resource_manager(self)
        self.rule_manager = RuleManager()
        self.rule_manager.set_resource_manager(self)
        # protocols that are requesting remote resource
        self.pending_protocols = []
        # protocols that are waiting request from remote resource
        self.waiting_protocols = []
        self.memory_to_protocol_map = {}

    def load(self, rule: "Rule") -> bool:
        """Method to load rules for entanglement management.

        Attempts to add rules to the rule manager.
        Will automatically execute rule action if conditions met on a memories.

        Args:
            rule (Rule): rule to load.

        Returns:
            bool: if rule was loaded successfully.
        """

        log.logger.info('{} load rule={}'.format(self.owner.name, rule))
        self.rule_manager.load(rule)

        for memory_info in self.memory_manager:  # iterate through each memories, and check if the rule is valid on each memories
            memories_info = rule.is_valid(memory_info)  # is valid means condition is satisfied
            if len(memories_info) > 0:
                rule.do(memories_info)
                for info in memories_info:
                    info.to_occupied()

        return True

    def expire(self, rule: "Rule") -> None:
        """Method to remove expired rule.

        Will update (remove) rule in rule manager.
        Will also update (remove) protocols connected to the rule (if they have already been created, and not finished yet).

        Args:
            rule (Rule): rule to remove.
        """

        log.logger.info('{} expire rule {}'.format(self.owner.name, rule))
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
                self.update(protocol, memory, MemoryInfo.RAW)

    def update(self, protocol: "EntanglementProtocol", memory: "Memory", state: str) -> None:
        """Method to update state of memories after completion of entanglement management protocol.

        Args:
            protocol (EntanglementProtocol): concerned protocol.
                If not None, then remove all references.
            memory (Memory): memories to update.
            state (str): new state for the memories.

        Side Effects:
            May modify memories state, and modify any attached protocols.
        """

        self.memory_manager.update(memory, state)
        if protocol:
            memory.detach(protocol)
            memory.attach(memory.memory_array)
            if protocol in protocol.rule.protocols:
                protocol.rule.protocols.remove(protocol)

        if protocol in self.owner.protocols:
            self.owner.protocols.remove(protocol)

        if protocol in self.waiting_protocols:
            self.waiting_protocols.remove(protocol)

        if protocol in self.pending_protocols:
            self.pending_protocols.remove(protocol)

        # iterate all the ruls and check if there is a valid rule
        memo_info = self.memory_manager.get_info_by_memory(memory)
        for rule in self.rule_manager:
            memories_info = rule.is_valid(memo_info)
            if len(memories_info) > 0:
                rule.do(memories_info)
                for info in memories_info:
                    info.to_occupied()
                return

        self.owner.get_idle_memory(memo_info)  # no new rules apply to this memories, thus "idle"

    def get_memory_manager(self):
        return self.memory_manager

    def send_request(self, protocol: "EntanglementProtocol", req_dst: Optional[str],
                     req_condition_func: RequestConditionFunc, req_args: Arguments):
        """Method to send protocol request to another node.

        Send the request to pair the local 'protocol' with the protocol on the remote node 'req_dst'.
        The function `req_condition_func` describes the desired protocol.

        Args:
            protocol (EntanglementProtocol): protocol sending the request.
            req_dst (str): name of destination node.
            req_condition_func (Callable[[list[EntanglementProtocol]], EntanglementProtocol]):
                function used to evaluate condition on distant node.
            req_args (dict[str, Any]): arguments for req_cond_func.
        """

        protocol.owner = self.owner
        if req_dst is None:
            self.waiting_protocols.append(protocol)
            return
        if protocol not in self.pending_protocols:
            self.pending_protocols.append(protocol)
        memo_names = [memo.name for memo in protocol.memories]
        msg = ResourceManagerMessage(ResourceManagerMsgType.REQUEST, protocol=protocol.name, node=self.owner.name,
                                     memories=memo_names, req_condition_func=req_condition_func, req_args=req_args)
        self.owner.send_message(req_dst, msg)
        log.logger.debug("{} send {} message to {}".format(self.owner.name, msg.msg_type.name, req_dst))

    def received_message(self, src: str, msg: "ResourceManagerMessage") -> None:
        """Method to receive resource manager messages.

        Messages come in 4 types, as detailed in the `ResourceManagerMessage` class.

        Args:
            src (str): name of the node that sent the message.
            msg (ResourceManagerMessage): message received.
        """

        log.logger.debug("{} resource manager receive message from {}: {}".format(self.owner.name, src, msg))
        if msg.msg_type is ResourceManagerMsgType.REQUEST:
            # select the wait-for-request protocol to respond to the message
            protocol = msg.req_condition_func(self.waiting_protocols, msg.req_args)
            if protocol is not None:
                protocol.set_others(msg.ini_protocol_name, msg.ini_node_name, msg.ini_memories_name)
                memo_names = [memo.name for memo in protocol.memories]
                new_msg = ResourceManagerMessage(ResourceManagerMsgType.RESPONSE, protocol=msg.ini_protocol_name,
                            node=msg.ini_node_name, memories=msg.ini_memories_name, is_approved=True,
                            paired_protocol=protocol.name, paired_node=self.owner.name, paired_memories=memo_names)
                self.owner.send_message(src, new_msg)
                self.waiting_protocols.remove(protocol)
                self.owner.protocols.append(protocol)
                protocol.start()
            else:
                # none of the self.waiting_protocol satisfy the req_condition_func --> is_approved=False
                new_msg = ResourceManagerMessage(ResourceManagerMsgType.RESPONSE, protocol=msg.ini_protocol_name,
                                                 node=msg.ini_node_name, memories=msg.ini_memories_name, is_approved=False,
                                                 paired_protocol=None, paired_node=None, paired_memories=None)
                self.owner.send_message(src, new_msg)

        elif msg.msg_type is ResourceManagerMsgType.RESPONSE:
            protocol_name = msg.ini_protocol_name

            protocol: Optional[EntanglementProtocol] = None
            for p in self.pending_protocols:
                if p.name == protocol_name:
                    protocol = p
                    break
            else:  # no matched pending protocols
                if msg.is_approved:
                    self.release_remote_protocol(src, msg.paired_protocol)
                return

            if msg.is_approved:
                protocol.set_others(msg.paired_protocol, msg.paired_node, msg.paired_memories)  # pairing (cost one round-trip-time)
                if protocol.is_ready():
                    self.pending_protocols.remove(protocol)
                    self.owner.protocols.append(protocol)
                    protocol.owner = self.owner
                    protocol.start()
            else:
                protocol.rule.protocols.remove(protocol)
                for memory in protocol.memories:
                    memory.detach(protocol)
                    memory.attach(memory.memory_array)
                    info = self.memory_manager.get_info_by_memory(memory)
                    if info.remote_node is None:
                        self.update(None, memory, MemoryInfo.RAW)
                    else:
                        self.update(None, memory, MemoryInfo.ENTANGLED)
                self.pending_protocols.remove(protocol)

        elif msg.msg_type is ResourceManagerMsgType.RELEASE_PROTOCOL:
            for p in self.owner.protocols:
                if p.name == msg.protocol:
                    p.release()

        elif msg.msg_type is ResourceManagerMsgType.RELEASE_MEMORY:
            target_id = msg.memory
            for protocol in self.owner.protocols:
                for memory in protocol.memories:
                    if memory.name == target_id:
                        protocol.release()
                        return

    def memory_expire(self, memory: "Memory"):
        """Method to receive memories expiration events."""

        self.update(None, memory, "RAW")

    def release_remote_protocol(self, dst: str, protocol: str) -> None:
        """Method to release protocols from memories on distant nodes.

        Release the remote protocol 'protocol' on the remote node 'dst'.
        The local protocol was paired with the remote protocol but local protocol becomes invalid.
        The resource manager needs to notify the remote node to cancel the paired protocol.

        Args:
            dst (str): name of the destination node.
            protocol (str): name of protocol to release on node.
        """

        msg = ResourceManagerMessage(ResourceManagerMsgType.RELEASE_PROTOCOL, protocol=protocol, node='', memories=[])
        self.owner.send_message(dst, msg)

    def release_remote_memory(self, dst: str, memory_id: str) -> None:
        """Method to release memories on distant nodes.

        Release the remote memories 'memory_id' on the node 'dst'.
        The entanglement protocol of remote memories was paired with the local protocol 'init_protocol', but local
        protocol becomes invalid.
        The resource manager needs to notify the remote node to release the occupied memories.

        Args:
            dst (str): name of destination node.
            memory_id (str): name of memories to release.
        """

        msg = ResourceManagerMessage(ResourceManagerMsgType.RELEASE_MEMORY, protocol="", 
                                     node="", memories=[], memory_id=memory_id)
        self.owner.send_message(dst, msg)

    def __str__(self) -> str:
        return self.name
