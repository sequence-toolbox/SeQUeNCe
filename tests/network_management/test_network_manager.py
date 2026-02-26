import math
from unittest.mock import Mock

from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.network_management.network_manager import *
from sequence.network_management.rsvp import RSVPMsgType
from sequence.protocol import StackProtocol
from sequence.topology.node import QuantumRouter, BSMNode
import pytest
from sequence.network_management.reservation import Reservation


class DistributedQuantumRouter(QuantumRouter):
    def __init__(self, name, timeline, memo_size=50):
        super().__init__(name, timeline, memo_size)
        self.send_log = []
        self.receive_log = []
        self.send_out = True

    def send_message(self, dst: str, msg: Message, priority=math.inf) -> None:
        self.send_log.append([dst, msg])
        if self.send_out:
            super().send_message(dst, msg, priority)

    def receive_message(self, src: str, msg: Message) -> None:
        if msg.receiver == "network_manager":
            self.receive_log.append((src, msg))
        super().receive_message(src, msg)

    def reset(self):
        self.send_log = []
        self.receive_log = []


class FakeProtocol(StackProtocol):
    def __init__(self, owner, name):
        super().__init__(owner, name)
        self.is_pop = False
        self.is_push = False

    def pop(self, **kwargs):
        self.is_pop = True

    def push(self, **kwargs):
        self.is_push = True

@pytest.fixture
def tl():
    return Timeline()

@pytest.fixture
def test_node(tl):
    node =  DistributedQuantumRouter("fake", tl)
    node.get_reservation_result = Mock()
    node.get_other_reservation = Mock()

    node.resource_manager.generate_load_rules = Mock()

    return node

@pytest.fixture
def mock_reservation(test_node):
    reservation = Mock(spec=Reservation)
    reservation.initiator = 'n1'
    reservation.responder = 'n2'
    reservation.path = ['n1', 'n2']
    reservation.start_time = 1e12
    reservation.end_time = 3e12
    reservation.memory_size = 50
    reservation.fidelity = 1
    return reservation



# Test the Network Manager basics
class TestNetworkManager:
    @pytest.mark.unit
    def test_network_manager_factory(self, test_node):
        assert NetworkManager._global_type == 'distributed'
        assert isinstance(test_node.network_manager, DistributedNetworkManager)

        with pytest.raises(NotImplementedError):
            NetworkManager.set_global_type('dne')

    @pytest.mark.unit
    def test_network_manager_timecards(self, test_node):
        tc = test_node.network_manager.get_timecards()
        assert len(tc) == 50
        assert all(isinstance(tc, MemoryTimeCard) for tc in tc)

    @pytest.mark.unit
    def test_network_manager_generate_rule(self, test_node, mock_reservation):
        mock_reservation.path = ['n1', 'n2']

        test_node.network_manager.generate_rules(mock_reservation)
        test_node.resource_manager.generate_load_rules.assert_called_once_with(mock_reservation.path, mock_reservation, test_node.network_manager.timecards, test_node.network_manager.memory_array_name)

# Test the default network manager
class TestDistributedNetworkManager:
    @pytest.mark.unit
    def test_protocol_stack(self, test_node):
        assert hasattr(test_node.network_manager, 'protocol_stack')
        assert len(test_node.network_manager.protocol_stack) == 2
        assert isinstance(test_node.network_manager.protocol_stack[0], ForwardingProtocol)
        assert isinstance(test_node.network_manager.protocol_stack[-1], RSVPProtocol)

    @pytest.mark.unit
    def test_routing_protocol(self, test_node):
        assert hasattr(test_node.network_manager, 'routing_protocol')
        assert test_node.network_manager.routing_protocol is not None

    @pytest.mark.unit
    def test_pop_approve_initiator(self, test_node, mock_reservation):
        mock_reservation.initiator = test_node.name
        inbound_msg = Mock()
        inbound_msg.msg_type = RSVPMsgType.APPROVE
        inbound_msg.reservation = mock_reservation

        test_node.network_manager.pop(msg=inbound_msg) # Call the func with mocks

        test_node.resource_manager.generate_load_rules.assert_called_once_with(mock_reservation.path, mock_reservation, test_node.network_manager.timecards, test_node.network_manager.memory_array_name)

        test_node.get_reservation_result.assert_called_once_with(mock_reservation, True)
        test_node.get_other_reservation.assert_not_called()

    def test_pop_approve_responder(self, test_node, mock_reservation):
        mock_reservation.responder = test_node.name
        inbound_msg = Mock()
        inbound_msg.msg_type = RSVPMsgType.APPROVE
        inbound_msg.reservation = mock_reservation

        test_node.network_manager.pop(msg=inbound_msg)
        test_node.get_other_reservation.assert_called_once_with(mock_reservation)
        test_node.get_reservation_result.assert_not_called()


    @pytest.mark.unit
    def test_pop_reject(self, test_node, mock_reservation):
        mock_reservation.initiator = test_node.name
        inbound_msg = Mock()
        inbound_msg.msg_type = RSVPMsgType.REJECT
        inbound_msg.reservation = mock_reservation

        test_node.network_manager.pop(msg=inbound_msg)

        test_node.get_reservation_result.assert_called_once_with(mock_reservation, False)

    def test_pop_approve_intermediate(self, test_node, mock_reservation):
        inbound_msg = Mock()
        inbound_msg.msg_type = RSVPMsgType.APPROVE
        inbound_msg.reservation = mock_reservation
        test_node.network_manager.pop(msg=inbound_msg)
        test_node.resource_manager.generate_load_rules.assert_called_once_with(mock_reservation.path, mock_reservation,
                                                                               test_node.network_manager.timecards,
                                                                               test_node.network_manager.memory_array_name)

        test_node.get_reservation_result.assert_not_called()
        test_node.get_other_reservation.assert_not_called()

    def test_NetworkManager_push(self, test_node, mock_reservation):
        outbound_msg = Mock()
        test_node.send_out = False
        assert len(test_node.send_log) == 0
        test_node.network_manager.push(dst="dst", msg=outbound_msg)
        assert len(test_node.send_log) == 1
        assert test_node.send_log[0][0] == "dst" and isinstance(test_node.send_log[0][1], NetworkManagerMessage)

    def test_NetworkManager_received_message(self, test_node):
       test_node.network_manager.protocol_stack[0].pop = Mock()
       payload = "test_payload"
       msg = NetworkManagerMessage(None, 'network_manager', payload)

       # Call received_message
       test_node.network_manager.received_message("source_node", msg)

       # Verify protocol stack was called with unpacked payload
       test_node.network_manager.protocol_stack[0].pop.assert_called_once_with(
           src="source_node",
           msg=payload  # Note: payload is unwrapped from NetworkManagerMessage
       )

    def test_NetworkManager(self):
        tl = Timeline(1e10)
        n1 = DistributedQuantumRouter("n1", tl, 50)
        n2 = DistributedQuantumRouter("n2", tl, 50)
        n3 = DistributedQuantumRouter("n3", tl, 20)
        m1 = BSMNode("m1", tl, ["n1", "n2"])
        m2 = BSMNode("m2", tl, ["n2", "n3"])
        n1.add_bsm_node(m1.name, n2.name)
        n2.add_bsm_node(m1.name, n1.name)
        n2.add_bsm_node(m2.name, n3.name)
        n3.add_bsm_node(m2.name, n2.name)

        for src in [n1, n2, n3, m1, m2]:
            for dst in [n1, n2, n3, m1, m2]:
                if src.name != dst.name:
                    cc = ClassicalChannel("cc_%s_%s" % (src.name, dst.name), tl,
                                          10, delay=1e5)
                    cc.set_ends(src, dst.name)

        qc = QuantumChannel("qc_n1_m1", tl, 0, 10)
        qc.set_ends(n1, m1.name)
        qc = QuantumChannel("qc_n2_m1", tl, 0, 10)
        qc.set_ends(n2, m1.name)
        qc = QuantumChannel("qc_n2_m2", tl, 0, 10)
        qc.set_ends(n2, m2.name)
        qc = QuantumChannel("qc_n3_m2", tl, 0, 10)
        qc.set_ends(n3, m2.name)

        n1.network_manager.routing_protocol.add_forwarding_rule("n2", "n2")
        n1.network_manager.routing_protocol.add_forwarding_rule("n3", "n2")
        n2.network_manager.routing_protocol.add_forwarding_rule("n1", "n1")
        n2.network_manager.routing_protocol.add_forwarding_rule("n3", "n3")
        n3.network_manager.routing_protocol.add_forwarding_rule("n1", "n2")
        n3.network_manager.routing_protocol.add_forwarding_rule("n2", "n2")

        tl.init()

        # approved request
        n1.network_manager.request("n3", 1e12, 2e12, 20, 0.9)
        tl.run()
        assert len(n1.send_log) == len(n1.receive_log) == 1
        assert n1.send_log[0][0] == "n2" and n1.receive_log[0][0] == "n2"
        assert n1.send_log[0][1].payload.payload.msg_type == RSVPMsgType.REQUEST
        assert n1.receive_log[0][1].payload.payload.msg_type == RSVPMsgType.APPROVE
        assert len(n2.send_log) == len(n2.receive_log) == 2
        assert n2.send_log[0][0] == "n3" and n2.receive_log[0][0] == "n1"
        assert n2.send_log[1][0] == "n1" and n2.receive_log[1][0] == "n3"
        assert len(n3.send_log) == len(n3.receive_log) == 1
        assert n3.send_log[0][0] == "n2" and n3.receive_log[0][0] == "n2"

        n1.reset()
        n2.reset()
        n3.reset()

        # rejected request
        n1.network_manager.request("n3", 3e12, 4e12, 50, 0.9)
        tl.run()
        assert len(n1.send_log) == len(n1.receive_log) == 1
        assert n1.send_log[0][0] == "n2" and n1.receive_log[0][0] == "n2"
        assert n1.send_log[0][1].payload.payload.msg_type == RSVPMsgType.REQUEST
        assert n1.receive_log[0][1].payload.payload.msg_type == RSVPMsgType.REJECT
        assert len(n2.send_log) == len(n2.receive_log) == 1
        assert n2.send_log[0][0] == "n1" and n2.receive_log[0][0] == "n1"

        n1.reset()
        n2.reset()
        n3.reset()

        n1.network_manager.request("n3", 5e12, 6e12, 25, 0.9)
        tl.run()
        assert len(n1.send_log) == len(n1.receive_log) == 1
        assert n1.send_log[0][0] == "n2" and n1.receive_log[0][0] == "n2"
        assert n1.send_log[0][1].payload.payload.msg_type == RSVPMsgType.REQUEST
        assert n1.receive_log[0][1].payload.payload.msg_type == RSVPMsgType.REJECT
        assert len(n2.send_log) == len(n2.receive_log) == 2
        assert n2.send_log[0][0] == "n3" and n2.receive_log[0][0] == "n1"
        assert n2.send_log[1][0] == "n1" and n2.receive_log[1][0] == "n3"
        assert len(n3.send_log) == len(n3.receive_log) == 1
        assert n3.send_log[0][0] == "n2" and n3.receive_log[0][0] == "n2"

