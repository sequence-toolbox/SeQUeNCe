from abc import ABC, abstractmethod
from typing import List
from numpy.random import random
from math import ceil

from sequence import topology
from sequence import timeline
from sequence import encoding
from sequence.topology import Node
from sequence.process import Process
from sequence.event import Event


class Protocol(ABC):
    def __init__(self, own: Node):
        self.upper_protocols = []
        self.lower_protocols = []
        self.own = own

    @abstractmethod
    def pop(self, **kwargs):
        '''
        information generated in current protocol is popped to
        all its parents protocols
        '''
        pass

    @abstractmethod
    def push(self, **kwargs):
        '''
        information generated in current protocol is pushed to
        all its child protocols
        '''
        pass

    def _push(self, **kwargs):
        for child in self.lower_protocols:
            child.push(**kwargs)

    def _pop(self, **kwargs):
        for parent in self.upper_protocols:
            parent.pop(**kwargs)
        return

    @abstractmethod
    def received_message(self, src: str, msg: List[str]):
        '''
        receive classical message from another node
        '''
        pass


class EntanglementGeneration(protocol):
    '''
    PROCEDURE:

    FIRST STAGE
    1. Preparation
        starting node sets memories to + state
        starting node sends NEGOTIATE message
            1. message type (string)
            2. quantum delay (int)
            3. memory max frequency (float)
            4. number of memories (int)
        other end node sets memories to + state
        other end node schedules second stage time
        other end node sends NEGOTIATE_ACK message
            1. message type (string)
            2. frequency to use (float)
            3. number of memories to use (int)
            4. start time (int)
            5. quantum delay to schedule second stage
        starting node schedules second stage time
    2. excite memories
        starting and other end node excite memories at start time
        middle node send MEAS_RES message when BSM excited
            1. message type (string)
            2. triggered time (int)
        confirmed bell state measurements collected for second stage

    SECOND STAGE
    3. flip states
        starting and other end node flip memory state
        new start time is set as current time
    4. excite memories again
        starting and other end node excite memories at new start time
        middle node sends MEAS_RES message (with same format)
    5. record successfull bell state measurement
        successfull BSM results are popped to entanglement swapping

    UNSCHEDULED:
    memories pushed from entanglement_swapping are added to first stage memory indices
    '''
    def __init__(self, own, **kwargs):
        super().__init__(self, own)
        self.middle = kwargs.get("middle_node", self.own.name)
        self.others = []
        self.memory_array = None

        self.qc_delay = 0
        self.frequency = 0
        self.start_time = -1
        self.quantum_delay = 0

        # first stage
        self.memory_indices_1 = []

        # second stage
        self.memory_indices_2 = []

        self.stage = 1
        self.running = False

    def init(self):
        print("EG protocol init on node {}".format(self.own.name))
        assert ((self.middle == self.own.name and len(self.others) == 2) or
                (self.middle != self.own.name and len(self.others) == 1))
        if self.own.name != self.middle:
            memory_array_name = "AtomMemoryArray" + self.middle
            self.memory_array = self.own.components[memory_array_name]
            self.frequency = self.memory_array.max_frequency
            self.memory_indices_1 = range(self.memory_array.num_memories)

    def push(self, info_type, **kwargs):
        index = kwargs.get("index")
        self.memory_indices_1.append(index)
        if not self.running:
            self.start()

    def pop(self, info_type, **kwargs):
        if info_type == "BSM_res":
            res = kwargs.get("res")
            time = kwargs.get("time")
            message = "EntanglementGeneration MEAS_RES {} {}".format(res, time)
            self.own.send_message(self.others[0], message)

        else:
            raise Exception("invalid info type {} popped to EntanglementGeneration on node {}".format(info_type, self.own.name))

    def start(self):
        assert self.own.name != self.middle, "EntanglementGeneration.start() called on middle node"
        self.stage = 1
        self.running = True
        
        # set all memories to + state
        state = [complex(1/sqrt(2)), complex(1/sqrt(2))]
        for index in self.memory_indices_1:
            self.memory_array[index].qstate.set_state(state)

        # send NEGOTIATE message
        qchannel = self.own.qchannels[self.middle]
        self.qc_delay = int(round(qchannel.distance / qchannel.light_speed))
        self.frequency = self.memory_array.max_frequency
        message = "EntanglementGeneration NEGOTIATE {} {} {}".format(self.qc_delay,
                                                                     self.frequency,
                                                                     len(self.memory_indices_1))
        self.own.send_message(self.others[0], message)

    def start_stage_2(self):
        self.stage = 2
        self.start_time = self.own.timeline.now()

        # flip state of all memories
        for index in self.memory_indices_2:
            self.memory_array[index].flip_state()

        # excite memories
        self.memory_excite()

        # schedule end
        time_delay = int(1e12 * (len(self.memory_indices_2) + 1) / self.frequency) + self.quantum_delay
        process = Process(self, "end", [])
        event = Event(self.start_time + time_delay, process)
        self.own.timeline.schedule(event)

    def end(self):
        while len(self.memory_indices_2) > 0:
            index = self.memory_indices_2.pop()
            if index != -1: self.memory_indices_1.append(index)

        if len(self.memory_indices_1) > 0:
            self.start()
        else:
            self.running = False

    def received_message(self, src: str, msg: List[str]):
        msg_type = msg[0]

        if msg_type == "NEGOTIATE":
            another_delay = int(msg[1])
            another_frequency = float(msg[2])
            another_mem_num = int(msg[3])

            # calculate start times based on delay
            qchannel = self.own.qchannels[self.middle]
            self.qc_delay = int(round(qchannel.distance / qchannel.light_speed))
            cc_delay = int(self.own.cchannels[self.others[0]].delay)
            
            start_delay_other = max(self.qc_delay, another_delay) - another_delay
            start_delay_self = max(self.qc_delay, another_delay) - self.qc_delay
            another_start_time = self.own.timeline.now() + cc_delay + start_delay_other
            self.start_time = self.own.timeline.now() + cc_delay + start_delay_self

            # calculate frequency based on min
            self.frequency = min(self.memory_array.max_frequency, another_frequency)
            self.memory_array.frequency = self.frequency

            # calculate number of memories to use
            num_memories = min(len(self.memory_indices_1), another_mem_num)
            self.memory_indices_1 = self.memory_indices_1[:num_memories]

            # call memory_excite (with updated parameters)
            self.memory_excite()

            # schedule start time for second stage
            self.quantum_delay = max(self.qc_delay, another_delay)
            time_delay = int(1e12 * (num_memories + 1) / self.frequency) + self.quantum_delay
            process = Process(self, "start_stage_2", [])
            event = Event(self.start_time + time_delay, process)
            self.own.timeline.schedule(event)

            # send message to other node
            message = "EntanglementGeneration NEGOTIATE_ACK {} {} {} {}".format(self.frequency,
                                                                                num_memories,
                                                                                another_start_time,
                                                                                quantum_delay)
            self.own.send_message(self.others[0], message)

        elif msg_type == "NEGOTIATE_ACK":
            # update parameters
            self.frequency = float(msg[1])
            num_memories = int(msg[2])
            self.start_time = int(msg[3])
            self.quantun_delay = int(msg[4])
            self.memory_indices_1 = self.memory_indices_1[:num_memories]

            # call memory_excite (with updated parameters)
            self.memory_excite()

            # schedule start time for second stage
            time_delay = int(1e12 * (num_memories + 1) / self.frequency) + self.quantum_delay
            process = Process(self, "start_stage_2", [])
            event = Event(self.start_time + time_delay, process)
            self.own.timeline.schedule(event)

        elif msg_type == "MEAS_RES":
            res = int(msg[1])
            time = int(msg[2])
            index = int(round((time - self.start_time - self.qc_delay) * self.frequency * 1e-12))

            if self.stage == 1:
                # if we haven't received a measurement result yet, add to second stage queue
                if self.memory_indices_1[index] != -1:
                    self.memory_indices_2.append(self.memory_indices_1[index])
                    self.memory_indices_1[index] = -1
                # if we've already received a measurement, remove from second stage
                else:
                    self.memory_indices_1[index] = self.memory_indices_2.pop()

            else:
                if self.memory_indices_2[index] != -1:
                    self._pop(memory_index=self.memory_indices_2[index], another_node=self.others[0])
                    self.memory_indices_2[index] = -1
                else:
                    # TODO: invalidate result sent to entanglement purification
                    pass

        else:
            raise Exception("Invalid message {} received by EntanglementGeneration on node {}".format(msg_type, self.own.name))

    def memory_excite(self):
        period = int(round(1e12 / self.frequency))
        time = self.start_time
        if self.stage == 1:
            indices = self.memory_indices_1
        else:
            indices = self.memory_indices_2

        for i in indices:
            process = Process(self.memory_array[i], "excite", [])
            event = Event(time, process)
            self.own.timeline.schedule(event)
            time += period


class EntanglementGenerationOld(Protocol):
    '''
    NEGOTIATE message is composed by:
        1. Type of message: NEGOTIATE
        2. Delay of quantum channel: int
        3. Frequency of memory: int
        4. The number of emit in this round: int
        5. Sender's time to emit
    NEGOTIATE_ACK message is composed by:
        1. Type of message: NEGOTIATE_ACK
        2. Delay of quantum channel: int
        3. Frequency of memory: int
        4. The number of emit in this round: int
        5. Sender's time to emit
    MEAS_RES message is composed by:
        1. Type of message: MEAS_RES
        2. Trigger time: int
        3. Triggered detector: int
    ENT_MEMO message is composed by:
        1. Type of message: ENT_MEMO
        2. Trigger time: int
        3. Index number of entangled memory: int
    '''
    def __init__(self, own, **kwargs):
        Protocol.__init__(self, own)
        self.middle = kwargs.get("middle", self.own.name)
        self.others = kwargs.get("others", [])
        self.memories = []
        self.waiting_bsm = []
        self.waiting_remote = {}
        self.memo_frequency = -1
        self.offset = 1
        self.results = []
        self.fidelity = kwargs.get("fidelity", 0)
        self.wait_start = True
        self.end_time = 0
        self.emit_num = None

    def init(self):
        print("EG protocol init")
        assert ((self.middle == self.own.name and len(self.others) == 2) or
                (self.middle != self.own.name and len(self.others) == 1))
        if self.middle != self.own.name:
            self.frequency = self.own.components["MemoryArray"].max_frequency
            # TEMPORARY: set all memories for entanglement generation
            self.memories = list(range(len(self.own.components["MemoryArray"])))

    def remove_expired_memory(self):
        while self.waiting_bsm and self.waiting_bsm[0][0] < self.own.timeline.now() - self.own.cchannels[self.middle].delay * 2:
            waiting = self.waiting_bsm.pop(0)
            self.memories.append(waiting[1])

        if self.emit_num == 0 and self.own.name < self.others[0] and not self.wait_start and self.memories:
            self.wait_start = True
            self.start()

    def start(self):
        self.wait_start = True
        assert self.middle != self.own.name
        assert len(self.memories) > 0
        self.cc_delay = round(self.own.cchannels[self.others[0]].delay)
        qchannel = self.own.qchannels[self.middle]
        self.qc_delay = round(qchannel.distance / qchannel.light_speed)

        self.remove_expired_memory()
        self.emit_num = len(self.memories)

        msg_type = "NEGOTIATE"
        self.start_time = int(max(self.end_time, self.own.timeline.now()) + self.cc_delay * 2 + self.offset)
        msg = "EntanglementGeneration {} {} {} {} {}".format(msg_type,
                                                             self.qc_delay,
                                                             self.frequency,
                                                             self.emit_num,
                                                             self.start_time)
        self.own.send_message(self.others[0], msg)

    def pop(self, info_type, **kwargs):
        if info_type == "BSM_res":
            res = kwargs.get("res")
            cur_time = kwargs.get("time")
            assert all(cur_time == result[0] for result in self.results)
            self.results.append([cur_time, res])
            if len(self.results) == 1:
                process = Process(self, "pop", ["SEND_TRIGGER"])
                event = Event(self.own.timeline.now() + 1, process)
                self.own.timeline.schedule(event)

        elif info_type == "SEND_TRIGGER":
            if len(self.results) == 1:
                resolution = self.own.components["BSM"].detectors[0].time_resolution
                assert resolution > 0
                msg = "EntanglementGeneration MEAS_RES {} {} {}".format(self.results[0][0],
                                                                        self.results[0][1],
                                                                        resolution)
                self.own.send_message(self.others[0], msg)
                self.own.send_message(self.others[1], msg)
            elif len(self.results) == 2:
                pass
            else:
                raise Exception("receive more than two BSM result at the same time")
            self.results = []
        else:
            raise Exception("EntanglementGeneration protocol gets unknown type of message: ", info_type, kwargs)

    def push(self, **kwargs):
        index = kwargs["index"]
        self.memories.append(index)
        if self.emit_num == 0 and self.own.name < self.others[0] and not self.wait_start:
            self.wait_start = True
            self.start()

    def schedule_write(self, time):
        assert self.emit_num > 0
        assert len(self.memories) > 0
        assert time >= self.end_time
        self.end_time = time
        index = self.memories.pop(0)
        self.emit_num -= 1
        process = Process(self.own.components["MemoryArray"][index], "write", [])
        event = Event(time, process)
        self.own.timeline.schedule(event)
        self.waiting_bsm.append([time + self.qc_delay, index])

        # schedule expiration
        process = Process(self, "remove_expired_memory", [])
        cc_delay = self.own.cchannels[self.middle].delay
        event = Event(time + self.qc_delay + cc_delay * 2 + self.offset, process)
        self.own.timeline.schedule(event)

        if self.emit_num > 0:
            next_time = time + ceil(1e9 / self.frequency)
            process = Process(self, "schedule_write", [next_time])
            event = Event(time, process)
            self.own.timeline.schedule(event)
        elif self.own.name < self.others[0] and len(self.memories) > 0:
            self.wait_start = True
            process = Process(self, "start", [])
            event = Event(time, process)
            self.own.timeline.schedule(event)

    def send_entangled_memory_id(self, time, memory_id):
        msg = "EntanglementGeneration ENT_MEMO {} {}".format(time, memory_id)
        self.own.send_message(self.others[0], msg)

    def received_message(self, src: str, msg: List[str]):
        msg_type = msg[0]

        if msg_type == "NEGOTIATE":
            another_qc_delay = int(msg[1])
            another_frequency = int(msg[2])
            another_emit_num = int(msg[3])
            another_start_time = int(msg[4])

            qchannel = self.own.qchannels[self.middle]
            self.qc_delay = round(qchannel.distance / qchannel.light_speed)
            self.start_time = another_start_time + another_qc_delay - self.qc_delay
            assert self.start_time >= self.own.timeline.now()

            self.another_qc_delay = another_qc_delay
            self.frequency = min(self.frequency, another_frequency)

            self.remove_expired_memory()
            self.emit_num = min(len(self.memories), another_emit_num)

            # response message
            msg_type = "NEGOTIATE_ACK"
            msg = "EntanglementGeneration {} {} {} {} {}".format(msg_type,
                                                                 self.qc_delay,
                                                                 self.frequency,
                                                                 self.emit_num,
                                                                 self.start_time)
            self.own.send_message(self.others[0], msg)

            # schedule write operation
            if self.emit_num > 0:
                self.schedule_write(self.start_time)

        elif msg_type == "NEGOTIATE_ACK":
            self.wait_start = False
            another_qc_delay = int(msg[1])
            another_frequency = int(msg[2])
            another_emit_num = int(msg[3])
            another_start_time = int(msg[4])

            assert self.start_time == another_start_time + another_qc_delay - self.qc_delay
            self.another_qc_delay = another_qc_delay
            self.frequency = min(self.frequency, another_frequency)
            self.emit_num = min(self.emit_num, another_emit_num)

            # schedule write operation
            if self.emit_num > 0:
                self.schedule_write(self.start_time)
            elif len(self.waiting_bsm) == 0:
                self.wait_start = True
                self.start()
        elif msg_type == "MEAS_RES":
            trigger_time = int(msg[1])
            resolution = int(msg[3])

            def binary_search(waiting_list, time):
                left, right = 0, len(waiting_list) - 1
                while left <= right:
                    mid = (left + right) // 2
                    if waiting_list[mid][0] == time:
                        return mid
                    elif waiting_list[mid][0] > time:
                        right = mid - 1
                    else:
                        left = mid + 1
                return left

            def valid_trigger_time(trigger_time, target_time, resolution):
                upper = target_time + resolution
                lower = 0
                if resolution % 2 == 0:
                    upper = min(upper, target_time + resolution // 2)
                    lower = max(lower, target_time - resolution // 2)
                else:
                    upper = min(upper, target_time + resolution // 2 + 1)
                    lower = max(lower, target_time - resolution // 2 + 1)
                if (upper / resolution) % 1 >= 0.5:
                    upper -= 1
                if (lower / resolution) % 1 < 0.5:
                    lower += 1
                return lower <= trigger_time <= upper

            index = binary_search(self.waiting_bsm, trigger_time)
            if index < len(self.waiting_bsm) and valid_trigger_time(trigger_time, self.waiting_bsm[index][0], resolution):
                self.send_entangled_memory_id(trigger_time, self.waiting_bsm[index][1])
                self.waiting_remote[trigger_time] = self.waiting_bsm.pop(index)[1]
            elif 0 <= index-1 < len(self.waiting_bsm) and valid_trigger_time(trigger_time, self.waiting_bsm[index-1][0], resolution):
                index = index - 1
                self.send_entangled_memory_id(trigger_time, self.waiting_bsm[index][1])
                self.waiting_remote[trigger_time] = self.waiting_bsm.pop(index)[1]
            else:
                print(self.own.timeline.now(), "unkown trigger", self.own.name, trigger_time, self.waiting_bsm)

            for _ in range(index):
                waiting = self.waiting_bsm.pop(0)
                i = waiting[1]
                self.memories.append(i)

        elif msg_type == "ENT_MEMO":
            trigger_time = int(msg[1])
            remote_memory_index = int(msg[2])
            local_memory_index = self.waiting_remote[trigger_time]
            local_memory = self.own.components["MemoryArray"][local_memory_index]
            local_memory.entangled_memory["node_id"] = self.others[0]
            local_memory.entangled_memory["memo_id"] = remote_memory_index
            local_memory.fidelity = self.fidelity
            self.waiting_remote.pop(trigger_time)
            self._pop(memory_index=local_memory_index, another_node=self.others[0])
        else:
            raise Exception("unknown message of type '{}' received by EntanglementGeneration on node '{}'"
                            .format(msg_type, self.own.name))


class BBPSSW(Protocol):
    '''
    BBPSSW use PING, PONG message to exchange classical information
    PING message is composed by five parts:
        1. Type of message: PING
        2. The index number of operated purification: integer
        3. Memory id of kept memory on message receiver: integer
        4. Memory id of measured memory on message receiver: integer
        5. Memory id of kept memory on message sender: integer
        6. Memory id of measured memory on message sender: integer
    PONG message is composed by four parts:
        1. Type of message: PONG
        2. The index number of operated purification: integer
        3. Fidelity after purification: float
        4. Memory id of kept memory on message receiver: integer
        5. Memory id of measured memory on message receiver: integer
    ASSUMPTION:
        1. Two nodes receive poped message from bottom layer before receive
           PING / PONG message
        2. Classical message
        3. nodes have different name
    '''

    def __init__(self, own, threshold):
        Protocol.__init__(self, own)
        self.threshold = threshold
        # self.purified_lists :
        # { node name : [ [index of memories after round i purificaiton] ]
        self.purified_lists = {}
        # self.waiting_list:
        # { round of purification : [ set( [ kept memory, measured memory ] ) }
        self.waiting_list = {}

    def init(self):
        pass

    def _pop(self, **kwargs):
        print(kwargs, "qualified")

    def pop(self, **kwargs):
        memory_index = kwargs["memory_index"]
        another_node = kwargs["another_node"]
        if another_node not in self.purified_lists:
            self.purified_lists[another_node] = []
        purified_list = self.purified_lists[another_node]
        if len(purified_list) == 0:
            purified_list.append([])

        local_memory = self.own.components['MemoryArray']
        cur_fidelity = local_memory[memory_index].fidelity

        if cur_fidelity < self.threshold:
            purified_list[0].append(memory_index)
        else:
            self._pop(memory_index=memory_index, another_node=another_node)

        if len(purified_list[0]) > 1 and self.own.name > another_node:
            self.start_round(0, another_node)

    def start_round(self, round_id, another_node):
        local_memory = self.own.components['MemoryArray']
        purified_list = self.purified_lists[another_node]
        if round_id not in self.waiting_list:
            self.waiting_list[round_id] = set()
        kept_memo = purified_list[round_id].pop()
        measured_memo = purified_list[round_id].pop()
        assert (local_memory[kept_memo].fidelity ==
                local_memory[measured_memo].fidelity)
        assert (local_memory[kept_memo].fidelity > 0.5)

        another_kept_memo = local_memory[kept_memo].entangled_memory['memo_id']
        another_measured_memo = local_memory[measured_memo].entangled_memory['memo_id']
        self.waiting_list[round_id].add((kept_memo, measured_memo))

        msg = "BBPSSW PING %d %d %d %d %d" % (round_id,
                                              another_kept_memo,
                                              another_measured_memo,
                                              kept_memo,
                                              measured_memo)
        # WARN: wait change of Node.send_message function
        self.own.send_message(dst=another_node, msg=msg)

    def push(self, **kwargs):
        pass

    def received_message(self, src: str, msg: List[str]):
        purified_list = self.purified_lists[src]
        # WARN: wait change of Node.receive_message
        # WARN: assume protocol name is discarded from msg list
        type_index = 0
        msg_type = msg[type_index]
        if msg_type == "PING":
            round_id = int(msg[type_index+1])
            kept_memo = int(msg[type_index+2])
            measured_memo = int(msg[type_index+3])
            fidelity = self.purification(round_id, kept_memo,
                                         measured_memo, purified_list)

            reply = "BBPSSW PONG %d %f %s %s" % (round_id,
                                                 fidelity,
                                                 msg[type_index+4],
                                                 msg[type_index+5])
            # WARN: wait change of Node.send_message function
            self.own.send_message(dst=src, msg=reply)

            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
                purified_list[round_id+1].remove(kept_memo)
        elif msg_type == "PONG":
            round_id = int(msg[type_index+1])
            fidelity = float(msg[type_index+2])
            kept_memo = int(msg[type_index+3])
            measured_memo = int(msg[type_index+4])
            self.update(round_id, fidelity, kept_memo,
                        measured_memo, purified_list)
            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
            if (round_id+1 < len(purified_list) and
                    len(purified_list[round_id+1]) > 1):
                self.start_round(round_id+1, src)
        else:
            raise Exception("BBPSSW protocol receives"
                            "unkown type of message: %s" % str(msg))

    def purification(self,
                     round_id: int,
                     kept_memo: int,
                     measured_memo: int,
                     purified_list: List[List[int]]) -> float:

        local_memory = self.own.components['MemoryArray']
        assert (local_memory[kept_memo].fidelity ==
                local_memory[measured_memo].fidelity)
        assert (local_memory[kept_memo].fidelity > 0.5)
        purified_list[round_id].remove(kept_memo)
        purified_list[round_id].remove(measured_memo)

        fidelity = local_memory[kept_memo].fidelity
        suc_prob = self.success_probability(fidelity)
        if random() < suc_prob:
            fidelity = round(self.improved_fidelity(fidelity), 6)
            local_memory[kept_memo].fidelity = fidelity

            if len(purified_list) <= round_id + 1:
                purified_list.append([])
            purified_list[round_id+1].append(kept_memo)
        else:
            fidelity = 0
            local_memory[kept_memo].fidelity = fidelity
            local_memory[kept_memo].entangled_memory['node_id'] = None
            local_memory[kept_memo].entangled_memory['memo_id'] = None
            self._push(index=kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory[measured_memo].entangled_memory['node_id'] = None
        local_memory[measured_memo].entangled_memory['memo_id'] = None
        self._push(index=measured_memo)
        return fidelity

    def update(self, round_id: int,
               fidelity: float, kept_memo: int,
               measured_memo: int, purified_list):

        local_memory = self.own.components['MemoryArray']
        self.waiting_list[round_id].remove((kept_memo, measured_memo))

        local_memory[kept_memo].fidelity = fidelity
        if fidelity == 0:
            local_memory[kept_memo].entangled_memory['node_id'] = None
            local_memory[kept_memo].entangled_memory['memo_id'] = None
            self._push(index=kept_memo)
        elif fidelity < self.threshold:
            if len(purified_list) <= round_id + 1:
                purified_list.append([])
            purified_list[round_id+1].append(kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory[measured_memo].entangled_memory['node_id'] = None
        local_memory[measured_memo].entangled_memory['memo_id'] = None
        self._push(index=measured_memo)

    @staticmethod
    def success_probability(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) page 14
        '''
        return F**2 + 2*F*(1-F)/3 + 5*((1-F)/3)**2

    @staticmethod
    def improved_fidelity(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) formula (18) page 14
        '''
        return (F**2 + ((1-F)/3)**2) / (F**2 + 2*F*(1-F)/3 + 5*((1-F)/3)**2)


if __name__ == "__main__":
    from numpy.random import seed

    # two nodes case
    # multiple nodes case
    seed(1)

    # dummy protocol for distribution of direct transmission
    class DummyParent(Protocol):

        def __init__(self, own):
            Protocol.__init__(self, own)
            self.another = ''
            self.counter = 100
            self.multi_nodes = False

        def pop(self, memory_index, another):
            for parent in self.upper_protocols:
                parent.pop(memory_index, another)

        def push(self, **kwargs):
            memory_index = kwargs.get("memory_index")
            local_memory = self.own.components['MemoryArray']
            local_memory[memory_index].fidelity = 0.6
            if self.multi_nodes:
                if self.own.name > self.another and memory_index < 20:
                    local_memory[memory_index].entangled_memory['memo_id'] = memory_index + 20
                elif self.own.name < self.another and memory_index >= 20:
                    local_memory[memory_index].entangled_memory['memo_id'] = memory_index - 20
                else:
                    return
            else:
                local_memory[memory_index].entangled_memory['memo_id'] = memory_index
            local_memory[memory_index].entangled_memory['node_id'] = self.another
            process = Process(self, 'pop', [memory_index, self.another])
            event = Event(self.counter*1e9, process)
            self.own.timeline.schedule(event)
            self.counter += 1

        def received_message(self, src, msg):
            pass

    def three_nodes_test():
        # create timeline
        tl = timeline.Timeline()

        # create nodes alice, bob, charlie
        alice = topology.Node("alice", tl)
        bob = topology.Node("bob", tl)
        charlie = topology.Node("charlie", tl)
        tl.entities.append(alice)
        tl.entities.append(bob)
        tl.entities.append(charlie)

        # create classical channels
        cc1 = topology.ClassicalChannel("cc1", tl, distance=1e3, delay=1e5)
        cc2 = topology.ClassicalChannel("cc2", tl, distance=1e3, delay=1e5)
        cc3 = topology.ClassicalChannel("cc3", tl, distance=1e3, delay=1e5)
        cc1.add_end(alice)
        cc1.add_end(charlie)
        cc2.add_end(bob)
        cc2.add_end(charlie)
        cc3.add_end(alice)
        cc3.add_end(bob)
        alice.assign_cchannel(cc1)
        charlie.assign_cchannel(cc1)
        bob.assign_cchannel(cc2)
        charlie.assign_cchannel(cc2)
        alice.assign_cchannel(cc3)
        bob.assign_cchannel(cc3)

        # create quantum channels
        qc1 = topology.QuantumChannel("qc1", tl, distance=1e3)
        qc2 = topology.QuantumChannel("qc2", tl, distance=1e3)
        alice.qchannels = {"charlie": qc1}
        bob.qchannels = {"charlie": qc2}

        # create memories on nodes
        NUM_MEMORY = 10
        FREQUENCY = int(1e6)
        memory_params_alice = {"fidelity": 0.6, "direct_receiver": qc1, "efficiency": 0.5}
        memory_params_bob = {"fidelity": 0.6, "direct_receiver": qc2, "efficiency": 0.5}
        alice_memo_array = topology.MemoryArray("alice memory array",
                                                tl, num_memories=NUM_MEMORY,
                                                memory_params=memory_params_alice,
                                                frequency=FREQUENCY)
        bob_memo_array = topology.MemoryArray("bob memory array",
                                              tl, num_memories=NUM_MEMORY,
                                              frequency=FREQUENCY,
                                              memory_params=memory_params_bob)
        alice.components['MemoryArray'] = alice_memo_array
        bob.components['MemoryArray'] = bob_memo_array
        qc1.set_sender(alice_memo_array)
        qc2.set_sender(bob_memo_array)

        # create BSM
        detectors = [{"efficiency": 0.7, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000}] * 2
        bsm = topology.BSM("charlie bsm", tl, encoding_type=encoding.ensemble, detectors=detectors)
        charlie.components['BSM'] = bsm
        qc1.set_receiver(bsm)
        qc2.set_receiver(bsm)

        # create alice protocol stack
        egA = EntanglementGeneration(alice, middle="charlie", others=["bob"], fidelity=0.6)
        bbpsswA = BBPSSW(alice, threshold=0.9)
        egA.upper_protocols.append(bbpsswA)
        bbpsswA.lower_protocols.append(egA)
        alice.protocols.append(egA)
        alice.protocols.append(bbpsswA)

        # create bob protocol stack
        egB = EntanglementGeneration(bob, middle="charlie", others=["alice"], fidelity=0.6)
        bbpsswB = BBPSSW(bob, threshold=0.9)
        egB.upper_protocols.append(bbpsswB)
        bbpsswB.lower_protocols.append(egB)
        bob.protocols.append(egB)
        bob.protocols.append(bbpsswB)

        # create charlie protocol stack
        egC = EntanglementGeneration(charlie, middle="charlie", others=["alice", "bob"])
        charlie.protocols.append(egC)

        # schedule events
        process = Process(egA, "start", [])
        event = Event(0, process)
        tl.schedule(event)

        # start simulation
        tl.init()
        tl.run()

        def print_memory(memoryArray):
            for i, memory in enumerate(memoryArray):
                print(i, memoryArray[i].entangled_memory, memory.fidelity)

        print('alice memory')
        print_memory(alice_memo_array)
        print(egA.waiting_bsm)
        print(egA.waiting_remote)
        print(egA.memories)
        print(egA.emit_num)
        print('bob memory')
        print_memory(bob_memo_array)
        print(egB.waiting_bsm)
        print(egB.waiting_remote)
        print(egB.memories)
        print(egB.emit_num)

    def multi_nodes_test(n: int):
        # create timeline
        tl = timeline.Timeline()

        # create nodes
        nodes = []
        for i in range(n):
            node = topology.Node("node %d" % i, tl)
            nodes.append(node)

        # create classical channel
        for i in range(n-1):
            cc = topology.ClassicalChannel("cc1", tl, distance=1e3, delay=1e5)
            cc.add_end(nodes[i])
            cc.add_end(nodes[i+1])
            nodes[i].assign_cchannel(cc)
            nodes[i+1].assign_cchannel(cc)

        # create memories on nodes
        NUM_MEMORY = 40
        memory_params = {"fidelity": 0.6}
        for node in nodes:
            memory = topology.MemoryArray("%s memory array" % node.name,
                                          tl, num_memories=NUM_MEMORY,
                                          memory_params=memory_params)
            node.components['MemoryArray'] = memory

        # create protocol stack
        dummys = []
        for i, node in enumerate(nodes):
            bbpssw = BBPSSW(node, threshold=0.9)
            if i > 0:
                dummy = DummyParent(node)
                dummy.multi_nodes = True
                dummy.another = "node %d" % (i-1)
                dummy.upper_protocols.append(bbpssw)
                bbpssw.lower_protocols.append(dummy)
                node.protocols.append(dummy)
                dummys.append(dummy)
            if i < len(nodes)-1:
                dummy = DummyParent(node)
                dummy.multi_nodes = True
                dummy.another = "node %d" % (i+1)
                dummy.upper_protocols.append(bbpssw)
                bbpssw.lower_protocols.append(dummy)
                node.protocols.append(dummy)
                dummys.append(dummy)

            node.protocols.append(bbpssw)

        # create entanglement
        for i in range(n-1):
            memo1 = nodes[i].components['MemoryArray']
            memo2 = nodes[i+1].components['MemoryArray']
            for j in range(int(NUM_MEMORY/2)):
                memo1[j+int(NUM_MEMORY/2)].entangled_memory = {'node_id': 'node %d' % (i+1), 'memo_id': j}
                memo2[j].entangled_memory = {'node_id': 'node %d' % i, 'memo_id': j+int(NUM_MEMORY/2)}

        # schedule events
        counter = 0
        for i in range(0, len(dummys), 2):
            dummy1 = dummys[i]
            dummy2 = dummys[i+1]
            for j in range(int(NUM_MEMORY/2)):
                e = Event(counter*(1e5), Process(dummy1, "pop", [j+int(NUM_MEMORY/2), dummy2.own.name]))
                tl.schedule(e)
                e = Event(counter*(1e5), Process(dummy2, "pop", [j, dummy1.own.name]))
                tl.schedule(e)
                counter += 1

        # start simulation
        tl.init()
        tl.run()

        def print_memory(memoryArray):
            for i, memory in enumerate(memoryArray):
                print(i, memoryArray[i].entangled_memory, memory.fidelity)

        for node in nodes:
            memory = node.components['MemoryArray']
            print(node.name)
            print_memory(memory)

    three_nodes_test()
    # multi_nodes_test(3)
