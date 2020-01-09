from abc import ABC, abstractmethod
from typing import List
from numpy.random import random
from math import ceil, sqrt

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
        self.own.protocols.append(self)

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


class EntanglementGeneration(Protocol):
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
        super().__init__(own)
        self.middles = kwargs.get("middles", [self.own.name])
        self.others = kwargs.get("others", []) # other node corresponding to each middle node
        self.memory_array = None

        self.qc_delays = [0] * len(self.others)
        self.frequencies = [0] * len(self.others)
        self.start_times = [-1] * len(self.others)
        self.emit_nums = [0] * len(self.others)
        self.fidelity = kwargs.get("fidelity", 0)
        self.stage_delays = kwargs.get("stage_delays", [0] * len(self.others))

        # TODO: remove len(self.others) multiplier
        self.memory_indices = [[] for _ in range(len(self.others))] # keep track of indices to work on
        self.memory_stage = [[] for _ in range(len(self.others))] # keep track of stages completed by each memory
        self.bsm_wait_time = [[] for _ in range(len(self.others))] # keep track of expected arrival time for bsm results
        self.bsm_res = [[] for _ in range(len(self.others))]
        self.wait_remote = [[] for _ in range(len(self.others))] # keep track of memories waiting for ent_memo

        # misc
        self.invert_map = {} # keep track of mapping from connected qchannels to adjacent nodes
        self.running = False # True if protocol currently processing at least 1 memory
        self.is_start = False

    def memory_belong_protocol(self, memory):
        return memory.direct_receiver and memory.direct_receiver.receiver.owner.name == self.middle

    def init(self):
        print("EG protocol init on node {}".format(self.own.name))
        assert ((self.middles[0] == self.own.name and len(self.others) == 2) or
                (self.middles[0] != self.own.name and len(self.others) == len(self.middles)))
        if self.own.name != self.middles[0]:
            print("\tEG protocol end node init")
            self.memory_array = self.own.components['MemoryArray']
            self.frequencies = [self.memory_array.max_frequency for _ in range(len(self.others))]

            # put memories in correct memory index list based on direct receiver
            # also build memory stage, bsm wait time, and bsm result lists
            self.invert_map = {value: key for key, value in self.own.qchannels.items()}
            print(self.invert_map)
            for memory_index in range(len(self.memory_array)):
                qchannel = self.memory_array[memory_index].direct_receiver
                another_index = self.middles.index(self.invert_map[qchannel])

                self.add_memory_index(another_index, memory_index)

    # used by init() and when memory pushed down
    def add_memory_index(self, another_index, memory_index):
        print("\t\tadd memory called")
        print("\t\tindices before:", self.memory_indices[another_index])
        self.memory_indices[another_index].append(memory_index)
        self.memory_stage[another_index].append(0)
        self.bsm_wait_time[another_index].append(-1)
        self.bsm_res[another_index].append(-1)
        print("\t\tindices after: ", self.memory_indices[another_index])

    # used when memory popped to upper protocol
    def remove_memory_index(self, another_index, memory_index):
        del self.memory_stage[another_index][memory_index]
        del self.bsm_wait_time[another_index][memory_index]
        del self.bsm_res[another_index][memory_index]
        return self.memory_indices[another_index].pop(memory_index)

    def push(self, **kwargs):
        index = kwargs.get("index")
        print("memory {} pushed back to entanglement generation".format(index))
        another_name = self.invert_map[self.memory_array[index].direct_receiver]
        another_index = self.middles.index(another_name)

        self.add_memory_index(another_index, index)
        
        if not self.running and self.is_start:
            self.start()

    def pop(self, info_type, **kwargs):
        if info_type == "BSM_res":
            res = kwargs.get("res")
            time = kwargs.get("time")
            resolution = self.own.components["BSM"].resolution
            message = "EntanglementGeneration MEAS_RES {} {} {}".format(res, time, resolution)
            for node in self.others:
                self.own.send_message(node, message)

        else:
            raise Exception("invalid info type {} popped to EntanglementGeneration on node {}".format(info_type, self.own.name))

    def start(self):
        assert self.own.name != self.middles[0], "EntanglementGeneration.start() called on middle node"
        self.is_start = True
        for i in range(len(self.others)):
            self.start_individual(i)

    def start_individual(self, another_index):
        print("EG protocol start on node {} with partner {}".format(self.own.name, self.others[another_index]))
        self.running = True

        if len(self.memory_indices[another_index]) > 0:
            # update memories
            self.update_memory_indices(another_index)

            # send NEGOTIATE message
            qchannel = self.own.qchannels[self.middles[another_index]]
            self.qc_delays[another_index] = int(round(qchannel.distance / qchannel.light_speed))
            message = "EntanglementGeneration NEGOTIATE {} {} {}".format(self.qc_delays[another_index],
                                                                         self.frequencies[another_index],
                                                                         len(self.memory_indices[another_index]))
            self.own.send_message(self.others[another_index], message)

        else:
            print("EG protocol end on node", self.own.name)
            self.running = False

    def update_memory_indices(self, another_index):
        print("EG protocol update_memories on node {}".format(self.own.name))
        print("\tmemory_indices:", self.memory_indices[another_index])
        print("\tmemory_stage:", self.memory_stage[another_index])
        print("\tbsm_res:", self.bsm_res[another_index])

        # update memories that have finished stage 1 and flip state
        finished_1 = [i for i, val in enumerate(self.bsm_res[another_index]) if val != -1 and self.memory_stage[another_index][i] == 0]
        print("finished_1:", finished_1)
        print("\tmemory indices:", [self.memory_indices[another_index][i] for i in finished_1])
        for i in finished_1:
            memory_index = self.memory_indices[another_index][i]
            self.memory_stage[another_index][i] = 1
            self.memory_array[memory_index].flip_state()

        # set each memory in stage 1 to + state (and reset bsm)
        starting = [i for i in range(len(self.bsm_res[another_index])) if i not in finished_1]
        print("starting:", starting)
        print("\tmemory indices:", [self.memory_indices[another_index][i] for i in starting])
        for i in starting:
            memory_index = self.memory_indices[another_index][i]
            self.memory_stage[another_index][i] = 0
            self.bsm_res[another_index][i] = -1
            self.memory_array[memory_index].reset()

    def received_message(self, src: str, msg: List[str]):
        # print(self.own.timeline.now(), self.own.name, src, msg)
        # TEMPORARY: ignore unkown src
        if not (src in self.others or src == self.middle):
            return False

        msg_type = msg[0]

        if msg_type == "NEGOTIATE":
            another_delay = int(msg[1])
            another_frequency = float(msg[2])
            another_mem_num = int(msg[3])

            another_index = self.others.index(src)

            # update memories
            self.update_memory_indices(another_index)

            # calculate start times based on delay
            qchannel = self.own.qchannels[self.middles[another_index]]
            self.qc_delays[another_index] = int(round(qchannel.distance / qchannel.light_speed))
            cc_delay = int(self.own.cchannels[src].delay)
            
            quantum_delay = max(self.qc_delays[another_index], another_delay)
            start_delay_other = quantum_delay - another_delay
            start_delay_self = quantum_delay - self.qc_delays[another_index]
            another_start_time = self.own.timeline.now() + cc_delay + start_delay_other
            self.start_times[another_index] = self.own.timeline.now() + cc_delay + start_delay_self

            # calculate frequency based on min
            self.frequencies[another_index] = min(self.frequencies[another_index], another_frequency)
            ## self.memory_arrays[another_index].frequency = self.frequencies[another_index]

            # calculate number of memories to use
            num_memories = min(len(self.memory_indices[another_index]), another_mem_num)
            self.emit_nums[another_index] = num_memories

            # call memory_excite (with updated parameters)
            self.memory_excite(another_index)

            # send message to other node
            message = "EntanglementGeneration NEGOTIATE_ACK {} {} {} {}".format(self.frequencies[another_index],
                                                                                num_memories,
                                                                                another_start_time,
                                                                                quantum_delay)
            self.own.send_message(src, message)

        elif msg_type == "NEGOTIATE_ACK":
            another_index = self.others.index(src)

            # update parameters
            self.frequencies[another_index] = float(msg[1])
            self.emit_nums[another_index] = int(msg[2])
            self.start_times[another_index] = int(msg[3])
            quantum_delay = int(msg[4])

            # call memory_excite (with updated parameters)
            self.memory_excite(another_index)

            # schedule start time for another start
            time_delay = int(1e12 * (self.emit_nums[another_index] + 1) / self.frequencies[another_index])
            time_delay += quantum_delay + int(self.own.cchannels[src].delay)
            time_delay += self.stage_delays[another_index]
            process = Process(self, "start_individual", [another_index])
            event = Event(self.start_times[another_index] + time_delay, process)
            self.own.timeline.schedule(event)

        elif msg_type == "MEAS_RES":
            res = int(msg[1])
            time = int(msg[2])
            resolution = int(msg[3])
            another_index = self.middles.index(src)

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

            index = min(range(len(self.bsm_wait_time[another_index])), key=lambda i: abs(self.bsm_wait_time[another_index][i] - time))
            length = len(self.bsm_wait_time[another_index])
            if not index < length and 1 <= index <= length:
                index -= 1

            if valid_trigger_time(time, self.bsm_wait_time[another_index][index], resolution):
                print("{} got message for index {}".format(self.own.name, index))

                if self.bsm_res[another_index][index] == -1:
                    self.bsm_res[another_index][index] = res

                elif self.memory_stage[another_index][index] == 1:
                    # TODO: notify upper protocol of +/- state
                    # remove index
                    memory_id = self.remove_memory_index(another_index, index)
                    self.wait_remote[another_index].append(memory_id)
                    print("sending 'ENT_MEMO {}' message from node {}, wait_remote length is {}".format(memory_id, self.own.name, len(self.wait_remote)))
                    # send message to other node
                    message = "EntanglementGeneration ENT_MEMO {}".format(memory_id)
                    self.own.send_message(self.others[another_index], message)

                else:
                    self.bsm_res[another_index][index] = -1

            else:
                print("invalid trigger received by EG on node {}".format(self.own.name))
                print("\ttrigger time: {}\texpected: {}".format(time, self.bsm_wait_time[another_index][index]))

        elif msg_type == "ENT_MEMO":
            remote_id = int(msg[1])
            another_index = self.others.index(src)

            local_id = self.wait_remote[another_index].pop(0)
            local_memory = self.memory_array[local_id]
            local_memory.entangled_memory["node_id"] = src
            local_memory.entangled_memory["memo_id"] = remote_id
            local_memory.fidelity = self.fidelity

            self._pop(memory_index=local_id, another_node=src)
            print("popping memory", local_id)

        else:
            raise Exception("Invalid message {} received by EntanglementGeneration on node {}".format(msg_type, self.own.name))

    def memory_excite(self, another_index):
        print("memory_excite called on node", self.own.name)
        period = int(round(1e12 / self.frequencies[another_index]))
        time = self.start_times[another_index]
        self.bsm_wait_time[another_index] = [-1] * self.emit_nums[another_index]

        for i in range(self.emit_nums[another_index]):
            memory_index = self.memory_indices[another_index][i]
            process = Process(self.memory_array[memory_index], "excite", [])
            event = Event(time, process)
            self.own.timeline.schedule(event)

            self.bsm_wait_time[another_index][i] = time + self.qc_delays[another_index]

            time += period

        print("\tbsm_wait_time:", self.bsm_wait_time[another_index])

        return True


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
        # print(self.own.timeline.now(), self.own.name, kwargs, "qualified")
        if len(self.upper_protocols) == 0 and self.own.name == 'e0':
            print(self.own.timeline.now(), self.own.name, kwargs, "qualified")
        super()._pop(**kwargs)

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
        assert (local_memory[kept_memo].fidelity == local_memory[measured_memo].fidelity)
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
        self.own.send_message(dst=another_node, msg=msg, priority=2)

    def push(self, **kwargs):
        self._push(**kwargs)

    def received_message(self, src: str, msg: List[str]):
        if not src in self.purified_lists:
            return
        purified_list = self.purified_lists[src]
        # WARN: wait change of Node.receive_message
        # WARN: assume protocol name is discarded from msg list
        type_index = 0
        msg_type = msg[type_index]
        if msg_type == "PING":
            round_id = int(msg[type_index + 1])
            kept_memo = int(msg[type_index + 2])
            measured_memo = int(msg[type_index + 3])
            if not (len(purified_list) > round_id and
                    kept_memo in purified_list[round_id] and
                    measured_memo in purified_list[round_id]):
                return False
            fidelity = self.purification(round_id, kept_memo,
                                         measured_memo, purified_list)

            reply = "BBPSSW PONG %d %f %s %s" % (round_id,
                                                 fidelity,
                                                 msg[type_index + 4],
                                                 msg[type_index + 5])
            # WARN: wait change of Node.send_message function
            self.own.send_message(dst=src, msg=reply, priority=2)

            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
                purified_list[round_id + 1].remove(kept_memo)
        elif msg_type == "PONG":
            round_id = int(msg[type_index + 1])
            fidelity = float(msg[type_index + 2])
            kept_memo = int(msg[type_index + 3])
            measured_memo = int(msg[type_index + 4])
            if round_id not in self.waiting_list or (kept_memo, measured_memo) not in self.waiting_list[round_id]:
                return False

            self.update(round_id, fidelity, kept_memo,
                        measured_memo, purified_list)
            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
            if (round_id + 1 < len(purified_list) and len(purified_list[round_id + 1]) > 1):
                self.start_round(round_id + 1, src)
        else:
            raise Exception("BBPSSW protocol receives"
                            "unkown type of message: %s" % str(msg))

        return True

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
            purified_list[round_id + 1].append(kept_memo)
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
            purified_list[round_id + 1].append(kept_memo)

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
        return F**2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3)**2

    @staticmethod
    def improved_fidelity(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) formula (18) page 14
        '''
        return (F**2 + ((1 - F) / 3)**2) / (F**2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3)**2)


class EntanglementSwapping(Protocol):
    '''
    Node will execute entanglement swapping protocol will when there are
    memories that are entangled with memories on node remote1 and remote2
    SWAP_RES message is composed by:
        1. Type of message: SWAP_RES
        2. Influenced memory of receiver: integer
        3. Fidelity after entanglement swap : float
        4. Entangled node after entanglement swap : str
        5. Entangled memory after entanglement swap: integer
    ASSUMPTION:
        1. The name of node is not null string
    '''
    def __init__(self, own: Node, remote1: str, remote2: str, known_nodes):
        Protocol.__init__(self, own)
        self.remote1 = remote1
        self.remote2 = remote2
        # self.waiting_memo1(2) stores memories that entangled with remote1(2)
        self.waiting_memo1 = []
        self.waiting_memo2 = []
        self.waiting_swap_res = {}
        self.known_nodes = known_nodes

    def init(self):
        pass

    def push(self, **kwargs):
        self._push(**kwargs)

    def _pop(self, **kwargs):
        super()._pop(**kwargs)

    def pop(self, memory_index: int, another_node: str):
        if another_node == self.remote1:
            self.waiting_memo1.append(memory_index)
        elif another_node == self.remote2:
            self.waiting_memo2.append(memory_index)
        elif another_node in self.known_nodes:
            self.waiting_swap_res[memory_index] = another_node
        else:
            self._pop(memory_index=memory_index, another_node=another_node)

        while self.waiting_memo1 and self.waiting_memo2:
            memo1 = self.waiting_memo1.pop()
            memo2 = self.waiting_memo2.pop()
            self.swap(memo1, memo2)
            self._push(index=memo1)
            self._push(index=memo2)

    def swap(self, memo_id1: int, memo_id2: int):
        memo1 = self.own.components["MemoryArray"][memo_id1]
        memo2 = self.own.components["MemoryArray"][memo_id2]

        suc_prob = self.success_probability()
        fidelity = 0
        if random() < suc_prob:
            fidelity = self.updated_fidelity(memo1.fidelity, memo2.fidelity)

        another_node_id1 = memo1.entangled_memory['node_id']
        another_memo_id1 = memo1.entangled_memory['memo_id']
        another_node_id2 = memo2.entangled_memory['node_id']
        another_memo_id2 = memo2.entangled_memory['memo_id']
        msg = "EntanglementSwapping SWAP_RES %d %f %s %d" % (another_memo_id1,
                                                             fidelity,
                                                             another_node_id2,
                                                             another_memo_id2)
        self.own.send_message(dst=another_node_id1, msg=msg, priority=3)
        msg = "EntanglementSwapping SWAP_RES %d %f %s %d" % (another_memo_id2,
                                                             fidelity,
                                                             another_node_id1,
                                                             another_memo_id1)
        self.own.send_message(dst=another_node_id2, msg=msg, priority=3)

    def received_message(self, src: str, msg: List[str]):
        if src not in self.known_nodes:
            return False
        type_index = 0
        msg_type = msg[type_index]
        if msg_type == "SWAP_RES":
            memo_id = int(msg[type_index + 1])
            fidelity = float(msg[type_index + 2])
            another_node = msg[type_index + 3]
            another_memo = int(msg[type_index + 4])

            self.waiting_swap_res.pop(memo_id)

            memory = self.own.components["MemoryArray"][memo_id]
            if fidelity == 0:
                self._push(index=memo_id)
            else:
                memory.fidelity = fidelity
                memory.entangled_memory['node_id'] = another_node
                memory.entangled_memory['memo_id'] = another_memo
                self._pop(memory_index=memo_id, another_node=another_node)
        else:
            raise Exception("Entanglement swapping protocol "
                            "receives unkown type of message: "
                            "%s" % str(msg))

        return True

    def __str__(self):
        return "EntanglementSwapping: remote1: %s;  remote2: %s; known_nodes: %s" % (self.remote1, self.remote2, self.known_nodes)

    @staticmethod
    def success_probability() -> float:
        '''
        A simple model for BSM success probability
        '''
        return 0.9

    @staticmethod
    def updated_fidelity(f1: float, f2: float) -> float:
        '''
        A simple model updating fidelity of entanglement
        '''
        return (f1 + f2) / 2 * 0.9


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
            memory_index = kwargs.get("index")
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
            event = Event(self.counter * 1e9, process)
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
        for i in range(n - 1):
            cc = topology.ClassicalChannel("cc1", tl, distance=1e3, delay=1e5)
            cc.add_end(nodes[i])
            cc.add_end(nodes[i + 1])
            nodes[i].assign_cchannel(cc)
            nodes[i + 1].assign_cchannel(cc)

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
                dummy.another = "node %d" % (i - 1)
                dummy.upper_protocols.append(bbpssw)
                bbpssw.lower_protocols.append(dummy)
                node.protocols.append(dummy)
                dummys.append(dummy)
            if i < len(nodes) - 1:
                dummy = DummyParent(node)
                dummy.multi_nodes = True
                dummy.another = "node %d" % (i + 1)
                dummy.upper_protocols.append(bbpssw)
                bbpssw.lower_protocols.append(dummy)
                node.protocols.append(dummy)
                dummys.append(dummy)

            node.protocols.append(bbpssw)

        # create entanglement
        for i in range(n - 1):
            memo1 = nodes[i].components['MemoryArray']
            memo2 = nodes[i + 1].components['MemoryArray']
            for j in range(int(NUM_MEMORY / 2)):
                memo1[j + int(NUM_MEMORY / 2)].entangled_memory = {'node_id': 'node %d' % (i + 1), 'memo_id': j}
                memo2[j].entangled_memory = {'node_id': 'node %d' % i, 'memo_id': j + int(NUM_MEMORY / 2)}

        # schedule events
        counter = 0
        for i in range(0, len(dummys), 2):
            dummy1 = dummys[i]
            dummy2 = dummys[i + 1]
            for j in range(int(NUM_MEMORY / 2)):
                e = Event(counter * (1e5), Process(dummy1, "pop", [j + int(NUM_MEMORY / 2), dummy2.own.name]))
                tl.schedule(e)
                e = Event(counter * (1e5), Process(dummy2, "pop", [j, dummy1.own.name]))
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

    def es_test():
        # create timeline
        tl = timeline.Timeline()
        n = 3

        # create nodes
        nodes = []
        for i in range(n):
            node = topology.Node("node_%d" % i, tl)
            nodes.append(node)

        # create classical channel
        for i in range(n):
            for j in range(n):
                if i >= j:
                    continue
                cc = topology.ClassicalChannel("cc_%d_%d" % (i, j), tl, distance=1e3, delay=1e5)
                cc.add_end(nodes[i])
                cc.add_end(nodes[j])
                nodes[i].assign_cchannel(cc)
                nodes[j].assign_cchannel(cc)

        # create memories on nodes
        NUM_MEMORY = 40
        memory_params = {"fidelity": 0.9}
        for node in nodes:
            memory = topology.MemoryArray("%s memory array" % node.name,
                                          tl, num_memories=NUM_MEMORY,
                                          memory_params=memory_params)
            node.components['MemoryArray'] = memory

        # create protocol stack
        esps = []
        esp = EntanglementSwapping(nodes[0], '', '')
        esps.append(esp)
        esp = EntanglementSwapping(nodes[1], 'node_0', 'node_2')
        esps.append(esp)
        esp = EntanglementSwapping(nodes[2], '', '')
        esps.append(esp)

        # create entanglement
        counter = 0
        for i in range(n - 1):
            memo1 = nodes[i].components['MemoryArray']
            memo2 = nodes[i + 1].components['MemoryArray']
            for j in range(int(NUM_MEMORY / 2)):
                memo1[j + int(NUM_MEMORY / 2)].entangled_memory = {'node_id': 'node_%d' % (i + 1), 'memo_id': j}
                memo2[j].entangled_memory = {'node_id': 'node_%d' % i, 'memo_id': j + int(NUM_MEMORY / 2)}

                # schedule events
                e = Event(counter * (1e6), Process(esps[i], "pop", [j + int(NUM_MEMORY / 2), esps[i + 1].own.name]))
                tl.schedule(e)
                e = Event(counter * (1e6), Process(esps[i + 1], "pop", [j, esps[i].own.name]))
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

    # three_nodes_test()
    # multi_nodes_test(3)
    es_test()
