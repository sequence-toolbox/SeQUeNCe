"""
Unit and Integration Tests for reservation.py
"""
from unittest.mock import Mock

import pytest
from numpy import random

from sequence.components.memory import MemoryArray
from sequence.kernel.timeline import Timeline
from sequence.network_management.reservation import Reservation, RSVPMsgType, ResourceReservationMessage, ResourceReservationProtocol, MemoryTimeCard, QCap
from sequence.topology.node import QuantumRouter

random.seed(42) # Set deterministic seed

@pytest.fixture
def tl():
    return Timeline()

@pytest.fixture
def std_reservation():
    return Reservation('a', 'b', 10, 20, 5, 0.9)

@pytest.fixture
def std_timecard():
    return MemoryTimeCard(0)

@pytest.fixture
def mock_owner():
    owner = Mock()
    owner.name = 'node1'
    owner.timeline = Mock()
    owner.timeline.now.return_value = 0
    owner.resource_manager = Mock()
    owner.components = {}
    owner.network_manager = Mock()
    return owner

@pytest.fixture
def mock_memory_array():
    memo_arr = Mock()
    memo_arr.__len__ = Mock(return_value=50)
    return memo_arr

def resource_res_protocol(mock_owner, mock_memory_array):
    mock_owner.components['memory_array'] = mock_memory_array
    proto = ResourceReservationProtocol(mock_owner, 'node1.rsvp', 'memory_array')
    proto._push = Mock()
    proto._pop = Mock()
    return proto


class FakeNode(QuantumRouter):
    def __init__(self, name, timeline, memo_size=50):
        super().__init__(name, timeline, memo_size)
        memo_arr_name = ''
        for name in self.components.keys():
            if type(self.components[name]) is MemoryArray:
                memo_arr_name = name
                break
        self.rsvp = ResourceReservationProtocol(self, self.name + '.rsvp', memo_arr_name)
        self.rsvp.upper_protocols.append(self)
        self.rsvp.lower_protocols.append(self)
        self.push_log = []
        self.pop_log = []

    def receive_message(self, src: str, msg: 'Message') -> None:
        if msg.receiver == 'network_manager':
            self.network_manager.received_message(src, msg)
        else:
            super().receive_message(src, msg)

    def push(self, **kwargs):
        self.push_log.append(kwargs)

    def pop(self, **kwargs):
        self.pop_log.append(kwargs)


class TestReservation:
    @pytest.mark.unit
    def test_init(self):
        res = Reservation('a', 'b', 10, 20, 5, 0.9, 100, 100)
        assert res.initiator == 'a'
        assert res.responder == 'b'
        assert res.start_time == 10
        assert res.end_time == 20
        assert res.memory_size == 5
        assert res.fidelity == 0.9
        assert res.entanglement_number == 100
        assert res.identity == 100
        assert res.path == []
        assert res.purification_mode == 'until_target'

    @pytest.mark.unit
    def test_invalid_init(self):
        with pytest.raises(AssertionError):
            Reservation('a', 'b', 20, 10, 5, 0.9)
        with pytest.raises(AssertionError):
            Reservation('a', 'b', 10, 20, 0, 0.9)

    @pytest.mark.unit
    def test_string_repr(self, std_reservation):
        assert str(std_reservation) == '|initiator=a; responder=b; start_time=10; end_time=20; memory_size=5; target_fidelity=0.9; entanglement_number=1; identity=0|'
        assert repr(std_reservation) == str(std_reservation)

    @pytest.mark.unit
    def test_equality(self, std_reservation):
        res1 = Reservation('a', 'b', 10, 20, 5, 0.9)
        assert std_reservation == res1

    @pytest.mark.unit
    def test_less_than(self, std_reservation):
        res1 = Reservation('a', 'b', 10, 20, 5, 0.9, identity=100)
        assert std_reservation < res1

    @pytest.mark.unit
    def test_hash(self, std_reservation):
        res = Reservation('a', 'b', 10, 20, 5, 0.9)
        assert hash(std_reservation) == hash(res)

    @pytest.mark.unit
    def test_set_path(self, std_reservation):
        path = ['a', 'b', 'c']
        std_reservation.set_path(path)
        assert path == std_reservation.path



@pytest.mark.unit
class TestMemoryTimeCard:
    def test_init(self):
         timecard = MemoryTimeCard(0)
         assert timecard.memory_index == 0
         assert timecard.reservations == []

    @pytest.mark.parametrize('start, end, expected_position', [
        (0, 5, 0), # Before std_reservation
        (25,30, 1), # After
        (10, 15, -1), # Overlap
        (5, 10, -1), # Boundary overlap
    ], ids=['before', 'after', 'overlap', 'boundary_overlap'])
    def test_schedule_reservation_iso(self, std_reservation, std_timecard, start, end, expected_position):
        std_timecard.reservations.insert(0, std_reservation)

        candidate = Reservation('a', 'b', start, end, 5, 0.9)
        assert std_timecard.schedule_reservation(candidate) == expected_position

    @pytest.mark.parametrize('start, end, expected_result', [
        (0, 5, True),  # Before std_reservation
        (25, 30, True),  # After
        (10, 15, False),  # Overlap
        (5, 10, False), # Boundary overlap
    ], ids=['before', 'after', 'overlap', 'boundary_overlap'])
    def test_add_integrated(self, std_timecard, std_reservation, start, end, expected_result):
        assert len(std_timecard.reservations) == 0

        assert std_timecard.add(std_reservation) == True
        assert len(std_timecard.reservations) == 1

        candidate = Reservation('a', 'b', start, end, 5, 0.9)
        assert std_timecard.add(candidate) == expected_result

        if expected_result:
            assert len(std_timecard.reservations) == 2
        else:
            assert len(std_timecard.reservations) == 1

    def test_remove(self, std_timecard, std_reservation):
        std_timecard.reservations.insert(0, std_reservation)
        assert len(std_timecard.reservations) == 1
        assert std_timecard.remove(std_reservation) == True # Remove to make it empty again
        assert len(std_timecard.reservations) == 0 # Ensure it's empty
        assert std_timecard.remove(std_reservation) == False # Triggers if value error, though it is NOT raised.

    def test_schedule_fuzzed(self, std_timecard):
        for _ in range(500):
            s_time = random.randint(100)
            duration = random.randint(24) + 1
            r = Reservation('a', 'b', s_time, s_time + duration, 1, 0.9)
            std_timecard.add(r)

        for i, r in enumerate(std_timecard.reservations):
            if i > 0:
                assert std_timecard.reservations[i - 1].end_time < r.start_time


@pytest.mark.unit
class TestQCap:
    def test_init(self):
        fake_qcap = QCap('n1')
        assert fake_qcap.node == 'n1'

@pytest.mark.unit
class TestRSVPMsgType:
    def test_members(self):
        assert RSVPMsgType.REQUEST.name == 'REQUEST'
        assert RSVPMsgType.REJECT.name == 'REJECT'
        assert RSVPMsgType.APPROVE.name == 'APPROVE'

    def test_uniqueness(self):
        members = list(RSVPMsgType)
        assert len(members) == 3
        assert len(set(m.value for m in members)) == 3 # Ensure members are unique

@pytest.mark.unit
class TestResourceReservationMessage:
    def test_init_request(self, std_reservation):
        msg = ResourceReservationMessage(RSVPMsgType.REQUEST, 'a', std_reservation)
        assert msg.msg_type == RSVPMsgType.REQUEST
        assert msg.receiver == 'a'
        assert msg.reservation == std_reservation
        assert hasattr(msg, 'qcaps')
        assert msg.qcaps == []
        assert not hasattr(msg, 'path')

    def test_init_reject(self, std_reservation):
        path = ['a', 'b']
        msg = ResourceReservationMessage(RSVPMsgType.REJECT, 'a', std_reservation, path=path)
        assert msg.msg_type == RSVPMsgType.REJECT
        assert msg.path == path

    def test_init_approve(self, std_reservation):
        path = ['a', 'b']
        msg = ResourceReservationMessage(RSVPMsgType.APPROVE, 'a', std_reservation, path=path)
        assert msg.msg_type == RSVPMsgType.APPROVE
        assert msg.path == path

    def test_init_unknown(self, std_reservation):
        with pytest.raises(Exception) as e:
            ResourceReservationMessage("INVALID_TYPE", "receiver", std_reservation) # type: ignore
        assert str(e.value) == "Unknown message type"

    def test_init_invalid_type(self, std_reservation):
        with pytest.raises(KeyError):
            ResourceReservationMessage(RSVPMsgType.APPROVE, 'a', std_reservation)
        with pytest.raises(KeyError):
            ResourceReservationMessage(RSVPMsgType.REJECT, 'a', std_reservation)

    def test_str_repr(self, std_reservation):
        msg = ResourceReservationMessage(RSVPMsgType.REQUEST, 'a', std_reservation)
        assert str(msg) == f'|type={msg.msg_type}; reservation={msg.reservation}|'


class TestResourceReservationProtocol:
    def test_init(self, mock_owner, mock_memory_array):
        mock_owner.components['mem_arr'] = mock_memory_array
        proto = ResourceReservationProtocol(mock_owner, 'node.rsvp', 'mem_arr')
        assert proto.owner == mock_owner
        assert proto.name == 'node.rsvp'
        assert proto.memory_array_name == 'mem_arr'
        assert proto.memo_arr == mock_memory_array
        assert proto.accepted_reservations == []

        assert len(proto.timecards) == 50


    def test_ResourceReservationProtocol_push(self):
        tl = Timeline()
        n1 = FakeNode('n1', tl)

        memo_arr = None
        for c in n1.components.values():
            if type(c) is MemoryArray:
                memo_arr = c
                break

        assert len(n1.rsvp.timecards) == len(memo_arr)
        n1.rsvp.push('n10', 1, 10, 1000, 0.9)
        assert n1.pop_log[0]['msg'].msg_type == RSVPMsgType.REJECT
        assert len(n1.push_log) == 0
        n1.rsvp.push('n10', 1, 10, 50, 0.9)
        assert n1.push_log[0]['msg'].msg_type == RSVPMsgType.REQUEST
        assert len(n1.pop_log) == 1
        for card in n1.rsvp.timecards:
            assert len(card.reservations) == 1
        n1.rsvp.push('n10', 5, 10, 1, 0.9)
        assert n1.pop_log[1]['msg'].msg_type == RSVPMsgType.REJECT
        assert len(n1.push_log) == 1
        n1.rsvp.push('n10', 20, 30, 1, 0.9)
        assert n1.push_log[1]['msg'].msg_type == RSVPMsgType.REQUEST
        assert len(n1.pop_log) == 2


    def test_ResourceReservationProtocol_pop(self):
        def reset(node):
            for card in node.rsvp.timecards:
                card.remove(reservation)
            node.push_log = []
            node.pop_log = []

        tl = Timeline()
        n1 = FakeNode('n1', tl)
        n1.map_to_middle_node['n0'] = 'm0'
        n1.map_to_middle_node['n2'] = 'm1'

        # intermediate node receives REQUEST and approve it
        reservation = Reservation('n0', 'n2', 1, 10, 25, 0.9)
        msg = ResourceReservationMessage(RSVPMsgType.REQUEST, n1.rsvp.name, reservation)
        msg.qcaps.append(QCap('n0'))
        n1.rsvp.pop('n0', msg)
        assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
        assert n1.push_log[0]['dst'] == 'n2'
        assert n1.push_log[0]['msg'].msg_type == RSVPMsgType.REQUEST
        assert len(n1.push_log[0]['msg'].qcaps) == 2
        for card in n1.rsvp.timecards:
            assert len(card.reservations) == 1
        reset(n1)

        # responder receives REQUEST and approve it
        reservation = Reservation('n0', 'n1', 1, 10, 50, 0.9)
        msg = ResourceReservationMessage(RSVPMsgType.REQUEST, n1.rsvp.name, reservation)
        msg.qcaps.append(QCap('n0'))
        n1.rsvp.pop('n0', msg)
        assert len(n1.pop_log) == 1 and len(n1.push_log) == 1
        assert n1.push_log[0]['next_hop'] == 'n0'
        assert n1.push_log[0]['msg'].msg_type == RSVPMsgType.APPROVE
        assert len(n1.push_log[0]['msg'].path) == 2
        for card in n1.rsvp.timecards:
            assert len(card.reservations) == 1
        reset(n1)

        # node receives REQUEST and reject it
        reservation = Reservation('n0', 'n2', 1, 10, 1000, 0.9)
        msg = ResourceReservationMessage(RSVPMsgType.REQUEST, n1.rsvp.name, reservation)
        msg.qcaps.append(QCap('n0'))
        n1.rsvp.pop('n0', msg)
        assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
        assert n1.push_log[0]['next_hop'] == 'n0'
        assert n1.push_log[0]['msg'].msg_type == RSVPMsgType.REJECT
        for card in n1.rsvp.timecards:
            assert len(card.reservations) == 0
        reset(n1)

        # initiator receives REJECT
        reservation = Reservation('n1', 'n2', 1, 10, 10, 0.9)
        for i, card in enumerate(n1.rsvp.timecards):
            if i < 10:
                card.add(reservation)
            else:
                break
        msg = ResourceReservationMessage(RSVPMsgType.REJECT, n1.rsvp.name, reservation, path=['n1', 'n2'])
        n1.rsvp.pop('n2', msg)
        assert len(n1.pop_log) == 1 and len(n1.push_log) == 0
        assert n1.pop_log[0]['msg'].msg_type == RSVPMsgType.REJECT
        for card in n1.rsvp.timecards:
            assert len(card.reservations) == 0
        reset(n1)

        # intermediate node receives REJECT
        reservation = Reservation('n0', 'n2', 1, 10, 10, 0.9)
        for i, card in enumerate(n1.rsvp.timecards):
            if i < 10:
                card.add(reservation)
            else:
                break
        msg = ResourceReservationMessage(RSVPMsgType.REJECT, n1.rsvp.name, reservation, path=['n0', 'n1', 'n2'])
        n1.rsvp.pop('n2', msg)
        assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
        assert n1.push_log[0]['msg'].msg_type == RSVPMsgType.REJECT
        for card in n1.rsvp.timecards:
            assert len(card.reservations) == 0
        reset(n1)

        # initiator receives APPROVE
        reservation = Reservation('n1', 'n2', 1, 10, 1000, 0.9)
        msg = ResourceReservationMessage(RSVPMsgType.APPROVE, n1.rsvp.name, reservation, path=['n1', 'n2'])
        n1.rsvp.pop('n2', msg)
        assert len(n1.pop_log) == 1 and len(n1.push_log) == 0
        assert n1.pop_log[0]['msg'].msg_type == RSVPMsgType.APPROVE
        reset(n1)

        # intermediate node receives APPROVE
        reservation = Reservation('n0', 'n2', 1, 10, 1000, 0.9)
        msg = ResourceReservationMessage(RSVPMsgType.APPROVE, n1.rsvp.name, reservation, path=['n0', 'n1', 'n2'])
        n1.rsvp.pop('n2', msg)
        assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
        assert n1.push_log[0]['next_hop'] == 'n0' and n1.push_log[0]['msg'].msg_type == RSVPMsgType.APPROVE
        reset(n1)


    def test_ResourceReservationProtocol_schedule(self):
        tl = Timeline()
        n1 = FakeNode('n1', tl)
        for _ in range(1000):
            s_time = random.randint(1000)
            memo_size = random.randint(25) + 1
            reservation = Reservation('', '', s_time, s_time + 1 + random.randint(200), memo_size, 0.9)
            if n1.rsvp.schedule(reservation):
                counter = 0
                for card in n1.rsvp.timecards:
                    if reservation in card.reservations:
                        counter += 1
                assert counter == memo_size * 2
            else:
                counter = 0
                for card in n1.rsvp.timecards:
                    if reservation in card.reservations:
                        counter += 1
                assert counter == 0

        n2 = FakeNode('n2', tl)
        for _ in range(1000):
            s_time = random.randint(1000)
            memo_size = random.randint(25) + 1
            reservation = Reservation('n2', '', s_time, s_time + 1 + random.randint(200), memo_size, 0.9)
            if n2.rsvp.schedule(reservation):
                counter = 0
                for card in n2.rsvp.timecards:
                    if reservation in card.reservations:
                        counter += 1
                assert counter == memo_size
            else:
                counter = 0
                for card in n2.rsvp.timecards:
                    if reservation in card.reservations:
                        counter += 1
                assert counter == 0