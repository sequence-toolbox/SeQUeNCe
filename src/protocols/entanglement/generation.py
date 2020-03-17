from typing import List

from ..message import Message
from ..protocol import Protocol
from ...kernel.event import Event
from ...kernel.process import Process


class EntanglementGenerationMessage(Message):
    def __init__(self, msg_type, **kwargs):
        self.msg_type = msg_type
        self.owner_type = type(EntanglementGeneration(None))

        if msg_type == "EXPIRE":
            self.mem_num = kwargs.get("mem_num")

        elif msg_type == "NEGOTIATE":
            self.qc_delay = kwargs.get("qc_delay")
            self.frequency = kwargs.get("frequency")
            self.num_memories = kwargs.get("num_memories")
            self.expired = kwargs.get("expired")
            self.finished = kwargs.get("finished")

        elif msg_type == "NEGOTIATE_ACK":
            self.frequency = kwargs.get("frequency")
            self.num_memories = kwargs.get("num_memories")
            self.start_time = kwargs.get("start_time")
            self.quantum_delay = kwargs.get("quantum_delay")
            self.expired = kwargs.get("expired")
            self.finished = kwargs.get("finished")

        elif msg_type == "MEAS_RES":
            self.res = kwargs.get("res")
            self.time = kwargs.get("time")
            self.resolution = kwargs.get("resolution")

        elif msg_type == "ENT_MEMO":
            self.id = kwargs.get("memory_id")
            self.time = kwargs.get("time")

        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(msg_type))


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

    MEMORY STAGE:
     0: starting protocol
     1: finished stage 1
     2: awaiting entanglement result
    -1: expired, awaiting recycling
    -2: popped, awaiting removal
    '''
    def __init__(self, own, **kwargs):
        if own is None:
            return

        super().__init__(own)
        self.middles = kwargs.get("middles", [self.own.name])
        self.others = kwargs.get("others", []) # other node corresponding to each middle node
        self.memory_array = None
        self.rsvp_name = 'EG'

        # network info
        self.fidelity = kwargs.get("fidelity", 0.9)
        self.stage_delays = kwargs.get("stage_delays", [])
        self.memory_destinations = None
        
        # misc
        self.is_start = False
        self.debug = False

    def init(self):
        if self.debug:
            print("EG protocol \033[1;36;40minit\033[0m on node", self.own.name)

        assert ((self.middles[0] == self.own.name and len(self.others) == 2) or
                (self.middles[0] != self.own.name and len(self.others) == len(self.middles)))

        self.set_params()

        if self.own.name != self.middles[0]:
            if self.debug:
                print("\tEG protocol end node init")

            self.memory_array = self.own.memory_array
            self.frequencies = [self.memory_array.max_frequency for _ in range(len(self.others))]

            if not self.memory_destinations:
                self.memory_destinations = [self.middles[0]] * len(self.memory_array)
            else:
                assert len(self.memory_destinations) == len(self.memory_array)

            # put memories in correct memory index list based on direct receiver
            # also build memory stage, bsm wait time, and bsm result lists
            # self.invert_map = {value: key for key, value in self.own.qchannels.items()}
            # for memory_index in range(len(self.memory_array)):
            #     qchannel = self.memory_array[memory_index].direct_receiver
            #     if qchannel is not None:
            #         another_index = self.middles.index(self.invert_map[qchannel])
            #         self.add_memory_index(another_index, memory_index)
            for memory_index in range(len(self.memory_array)):
                destination = self.memory_destinations[memory_index]
                if destination:
                    another_index = self.middles.index(destination)
                    self.add_memory_index(another_index, memory_index)

    def set_params(self):
        # network info
        self.qc_delays = [0] * len(self.others)
        self.frequencies = [0] * len(self.others)
        self.start_times = [-1] * len(self.others)
        self.emit_nums = [0] * len(self.others)
        self.stage_delays = [0] * len(self.others)

        # memory internal info
        self.memory_indices = [[] for _ in range(len(self.others))] # keep track of indices to work on
        self.memory_stage = [[] for _ in range(len(self.others))] # keep track of stages completed by each memory
        self.bsm_wait_time = [[] for _ in range(len(self.others))] # keep track of expected arrival time for bsm results
        self.bsm_res = [[] for _ in range(len(self.others))]
        self.wait_remote = [[] for _ in range(len(self.others))] # keep track of memories waiting for ent_memo
        self.wait_remote_times = [[] for _ in range(len(self.others))] # keep track of time for said memories
        self.add_list = [[] for _ in range(len(self.others))] # keep track of memories to be added

        # misc
        self.running = [False] * len(self.others) # True if protocol currently processing at least 1 memory

    # used by init() and when memory pushed down
    def add_memory_index(self, another_index, memory_index):
        self.memory_indices[another_index].append(memory_index)
        self.memory_stage[another_index].append(0)
        self.bsm_res[another_index].append(-1)
        self.memory_array[memory_index].reset()

    # used when memory popped to upper protocol and by expiration
    def remove_memory_index(self, another_index, memory_internal_index):
        del self.memory_stage[another_index][memory_internal_index]
        del self.bsm_res[another_index][memory_internal_index]
        del self.memory_indices[another_index][memory_internal_index]

    # used by expiration or when entanglement fails
    def recycle_memory_index(self, another_index, memory_index):
        memory_internal_index = self.memory_indices[another_index].index(memory_index)
        self.remove_memory_index(another_index, memory_internal_index)
        self.add_memory_index(another_index, memory_index)

    # used after change direct_receiver of memory
    def remove_memories(self, memories):
        for memory_index in memories:
            another_index, pos = None, None
            for i, index in enumerate(self.memory_indices):
                for j, memory in enumerate(index):
                    if memory == memory_index:
                        another_index, pos = i, j
                        break
                if another_index is not None:
                    break
            if another_index is not None:
                self.remove_memory_index(another_index, pos)

    # used after change direct_receiver of memory
    def add_memories(self, memories, qchannel, stop_time):
        for memory_index in memories:
            another_index = self.middles.index(self.invert_map[qchannel])
            self.add_memory_index(another_index, memory_index)
            self.memory_stop_time[memory_index] = stop_time

    def push(self, **kwargs):
        index = kwargs.get("index")

        if self.debug:
            print("EG protocol \033[1;36;40mpush\033[0m on node", self.own.name)
            print("\tmemory index:", index)

        another_name = self.invert_map[self.memory_array[index].direct_receiver]
        another_index = self.middles.index(another_name)

        # queue memory to be added to active memories
        self.add_list[another_index].append(index)

        # restart if necessary
        if not self.running[another_index] and self.is_start:
            if self.debug:
                print("\trestarting protocol")
            self.start_individual(another_index)

    def pop(self, info_type, **kwargs):
        if info_type == "BSM_res":
            res = kwargs.get("res")
            time = kwargs.get("time")
            resolution = self.own.bsm.resolution
            
            message = EntanglementGenerationMessage("MEAS_RES", res=res, time=time, resolution=resolution)
            for node in self.others:
                self.own.send_message(node, message)

        elif info_type == "expired_memory":
            index = kwargs.get("index")
            another_name = self.invert_map[self.memory_array[index].direct_receiver]
            another_index = self.middles.index(another_name)

            if self.debug:
                print("memory {} \033[1;31;40mexpired\033[0m on node {}".format(index, self.own.name))

            # if currently working, set to recycle
            if index in self.memory_indices[another_index]:
                memory_index = self.memory_indices[another_index].index(index)
                self.memory_stage[another_index][memory_index] = -1

            # if not currently working, queue to be added
            elif index not in self.add_list[another_index]:
                another_memory = self.memory_array[index].entangled_memory["memo_id"]
                self.add_list[another_index].append(index)

                # message = "EntanglementGeneration EXPIRE {}".format(another_memory)
                message = EntanglementGenerationMessage("EXPIRE", mem_num=another_memory)
                self.own.send_message(self.others[another_index], message)

                if self.debug:
                    print("\tother memory:", another_memory)

            # restart if necessary
            if not self.running[another_index] and self.is_start:
                self.start_individual(another_index)

        else:
            raise Exception("invalid info type {} popped to EntanglementGeneration on node {}".format(info_type, self.own.name))

    def start(self):
        assert self.own.name != self.middles[0], "EntanglementGeneration.start() called on middle node"
        assert self.rsvp_name != ''
        if self.is_start:
            for i in range(len(self.others)):
                self.start_individual(i)

    def start_individual(self, another_index):
        if self.debug:
            print("EG protocol \033[1;36;40mstart\033[0m on node {} with partner {}".format(self.own.name, self.others[another_index]))

        self.running[another_index] = True

        if len(self.memory_indices[another_index]) > 0:
            # update memories
            self.update_memory_indices(another_index)

            # compile lists
            expired = [i for i, val in enumerate(self.memory_stage[another_index]) if val == -1]
            finished = [i for i, val in enumerate(self.memory_stage[another_index]) if val == -2]

            # send NEGOTIATE message
            qchannel = self.own.qchannels[self.middles[another_index]]
            self.qc_delays[another_index] = int(round(qchannel.distance / qchannel.light_speed))
            message = EntanglementGenerationMessage("NEGOTIATE", qc_delay=self.qc_delays[another_index], frequency=self.frequencies[another_index],
                                                    num_memories=len(self.memory_indices[another_index]), expired=expired, finished=finished)

            self.own.send_message(self.others[another_index], message)

        else:
            print("EG protocol end on node", self.own.name)
            self.running[another_index] = False

    def update_memory_indices(self, another_index):
        if self.debug:
            print("EG protocol \033[1;36;40mupdate_memories\033[0m on node {}".format(self.own.name))
            print("\t\tmemory_indices:", self.memory_indices[another_index])
            print("\t\tmemory_stage:", self.memory_stage[another_index])
            print("\t\tbsm_res:", self.bsm_res[another_index])

        # update memories that have finished stage 1 and flip state
        finished_1 = [i for i, val in enumerate(self.bsm_res[another_index]) if val != -1 and self.memory_stage[another_index][i] == 0]
        if self.debug:
            print("\tfinished_1:", finished_1)
            print("\t\tmemory indices:", [self.memory_indices[another_index][i] for i in finished_1])
            print("\t\tstages:", [self.memory_stage[another_index][i] for i in finished_1])
            print("\t\tbsm res:", [self.bsm_res[another_index][i] for i in finished_1])
        for i in finished_1:
            memory_index = self.memory_indices[another_index][i]
            self.memory_stage[another_index][i] = 1
            self.memory_array[memory_index].flip_state()

        # set each memory in stage 1 to + state (and reset bsm)
        starting = [i for i, val in enumerate(self.memory_stage[another_index]) if i not in finished_1 and (val == 0 or val == 1)]
        if self.debug:
            print("\tstarting:", starting)
            print("\t\tmemory indices:", [self.memory_indices[another_index][i] for i in starting])
        for i in starting:
            memory_index = self.memory_indices[another_index][i]
            self.memory_stage[another_index][i] = 0
            self.bsm_res[another_index][i] = -1
            self.memory_array[memory_index].reset()

    def memory_excite(self, another_index):
        if self.debug:
            print("EG protocol \033[1;36;40mmemory_excite\033[0m on node", self.own.name)
            print("\tmemories:", self.memory_indices[another_index])
            print("\tstages:", self.memory_stage[another_index])

        period = int(round(1e12 / self.frequencies[another_index]))
        time = self.start_times[another_index]
        self.bsm_wait_time[another_index] = [-1] * self.emit_nums[another_index]

        for i in range(self.emit_nums[another_index]):
            # TODO: write condition more succinctly?
            if self.memory_stage[another_index][i] >= 0 and self.memory_stage[another_index][i] != 2:
                memory_index = self.memory_indices[another_index][i]
                process = Process(self.memory_array[memory_index], "excite", [])
                event = Event(time, process)
                self.own.timeline.schedule(event)

                self.bsm_wait_time[another_index][i] = time + self.qc_delays[another_index]

            time += period

        if self.debug:
            print("\tbsm_wait_time:", self.bsm_wait_time[another_index])

        return True

    def send_qubit(self, qubit, index):
        destination = self.memory_destinations[index]
        self.own.send_qubit(destination, qubit)

    def received_message(self, src: str, msg: List[str]):
        if self.debug:
            print("EG protocol \033[1;36;40mreceived_message\033[0m on node {}".format(self.own.name))
            print("\tsource:", src)
            print("\t\033[1;32;40mtype\033[0m:", msg.msg_type)
            # print("\tcontent:", msg[1:])

        # TEMPORARY: ignore unkown src
        if not (src in self.others or src in self.middles):
            return False

        msg_type = msg.msg_type

        if msg_type == "EXPIRE":
            self_mem_num = msg.mem_num
            another_index = self.others.index(src)

            # if not working, add to queue
            if self_mem_num not in self.add_list[another_index]:
                self.add_list[another_index].append(self_mem_num)

            # restart if necessary
            if not self.running[another_index] and self.is_start:
                self.start_individual(another_index)

        elif msg_type == "NEGOTIATE":
            another_delay = msg.qc_delay
            another_frequency = msg.frequency
            another_mem_num = msg.num_memories

            # get expired and finished lists
            another_expired = msg.expired
            another_finished = msg.finished

            another_index = self.others.index(src)

            # update necessary memories
            self.update_memory_indices(another_index)

            expired = [i for i, val in enumerate(self.memory_stage[another_index]) if val == -1]
            finished = [i for i, val in enumerate(self.memory_stage[another_index]) if val == -2]
            combined = list(set(expired + finished + another_expired + another_finished))
            combined.sort(reverse=True)
            expired_total = []
            finished_total = []

            if combined:
                for i in combined:
                    if i in expired or i in another_expired:
                        self.recycle_memory_index(another_index, self.memory_indices[another_index][i])
                        expired_total.append(i)
                    else:
                        self.remove_memory_index(another_index, i)
                        another_mem_num -= 1
                        finished_total.append(i)

            while len(self.add_list[another_index]) > 0:
                index = self.add_list[another_index].pop(0)
                if index not in self.memory_indices[another_index]:
                    self.add_memory_index(another_index, index)

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

            # calculate number of memories to use
            num_memories = min(len(self.memory_indices[another_index]), another_mem_num)
            self.emit_nums[another_index] = num_memories

            # call memory_excite (with updated parameters)
            self.memory_excite(another_index)

            # send message to other node
            message = EntanglementGenerationMessage("NEGOTIATE_ACK", frequency=self.frequencies[another_index], num_memories=num_memories,
                                                    start_time=another_start_time, quantum_delay=quantum_delay, expired=expired_total, finished=finished_total)
            self.own.send_message(src, message)

        elif msg_type == "NEGOTIATE_ACK":
            another_index = self.others.index(src)

            # update parameters
            self.frequencies[another_index] = msg.frequency
            self.emit_nums[another_index] = msg.num_memories
            self.start_times[another_index] = msg.start_time
            quantum_delay = msg.quantum_delay

            # get expired and finished lists
            expired_total = msg.expired
            finished_total = msg.finished

            combined = list(set(expired_total + finished_total))
            combined.sort(reverse=True)
            if combined:
                for i in combined:
                    if i in expired_total:
                        self.recycle_memory_index(another_index, self.memory_indices[another_index][i])
                    else:
                        self.remove_memory_index(another_index, i)

            while len(self.add_list[another_index]) > 0:
                index = self.add_list[another_index].pop(0)
                if index not in self.memory_indices[another_index]:
                    self.add_memory_index(another_index, index)

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
            res = msg.res
            time = msg.time
            resolution = msg.resolution
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

            if len(self.bsm_wait_time[another_index]) > 0:
                index = min(range(len(self.bsm_wait_time[another_index])), key=lambda i: abs(self.bsm_wait_time[another_index][i] - time))
                length = len(self.bsm_wait_time[another_index])
                if not index < length and 1 <= index <= length:
                    index -= 1

                if valid_trigger_time(time, self.bsm_wait_time[another_index][index], resolution):
                    if self.debug:
                        print("EG protocol valid trigger on node", self.own.name)
                        print("\ttrigger time: {}\tindex: {}".format(time, index))

                    if self.bsm_res[another_index][index] == -1:
                        self.bsm_res[another_index][index] = res

                    elif self.memory_stage[another_index][index] == 1:
                        # TODO: notify upper protocol of +/- state
                        self.memory_stage[another_index][index] = 2
                        memory_id = self.memory_indices[another_index][index]
                        self.wait_remote[another_index].append(memory_id)
                        self.wait_remote_times[another_index].append(time)
                        # send message to other node
                        # message = "EntanglementGeneration ENT_MEMO {} {}".format(memory_id, time)
                        message = EntanglementGenerationMessage("ENT_MEMO", memory_id=memory_id, time=time)
                        self.own.send_message(self.others[another_index], message)
                        
                        if self.debug:
                            print("EG protocol sending ENT_MEMO for memory {} on node {}".format(memory_id, self.own.name))
                            print("\twait remote:", self.wait_remote[another_index])

                    else:
                        self.bsm_res[another_index][index] = -1

                elif self.debug:
                    print("\033[1;33;40mWARNING\033[0m: invalid trigger received by EG on node {}".format(self.own.name))
                    print("\ttrigger time: {}\texpected: {}".format(time, self.bsm_wait_time[another_index][index]))

            elif self.debug:
                print("\033[1;33;40mWARNING\033[0m: invalid trigger received by EG on node {}".format(self.own.name))
                print("\ttrigger time: {}".format(time))   

        elif msg_type == "ENT_MEMO":
            remote_id = msg.id
            remote_time = msg.time
            another_index = self.others.index(src)

            if self.debug:
                print("EG protocol received ENT_MEMO for memory {} from node {}".format(remote_id, src))
                print("\twait_remote:", self.wait_remote[another_index])

            # check if the entanglement time is valid, if so pop to upper protocol
            if remote_time in self.wait_remote_times[another_index]:
                # get proper indices and clean wait_remote lists
                wait_remote_index = self.wait_remote_times[another_index].index(remote_time)
                local_id = self.wait_remote[another_index].pop(wait_remote_index)
                del self.wait_remote_times[another_index][wait_remote_index]

                # mark memory for deletion
                local_id_index = self.memory_indices[another_index].index(local_id)
                # self.remove_memory_index(another_index, local_id_index)
                self.memory_stage[another_index][local_id_index] = -2

                local_memory = self.memory_array[local_id]
                local_memory.entangled_memory["node_id"] = src
                local_memory.entangled_memory["memo_id"] = remote_id
                local_memory.fidelity = self.fidelity
                self._pop(memory_index=local_id, another_node=src)

                if self.debug:
                    print("EG protocol popping on node", self.own.name)
                    print("\tmemory_index: {}\tanother_node: {}".format(local_id, src))

        else:
            raise Exception("WARNING: Invalid message {} received by EG on node {}".format(msg_type, self.own.name))

        return True


