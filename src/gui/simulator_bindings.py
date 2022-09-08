"""
A Class which serves as the interface between the SeQUeNCe simulator
and GUI components
"""

import time
import os
import pandas as pd
from ..topology.node import *
from ..kernel.timeline import Timeline
from ..topology.topology import Topology
from ..app.random_request import RandomRequestApp
from ..utils.log import *

DIRECTORY, _ = os.path.split(__file__)


class GUI_Sim:
    def __init__(self, sim_time: int, time_scale: int, logging: str, sim_name, config):
        self.sim_name = sim_name
        self.time_scale = time_scale
        self.timeline = Timeline(sim_time * time_scale)
        self.timeline.seed(0)
        self.topology = Topology(sim_name, self.timeline)
        self.sim_templates = config.defaults.copy()
        self.apps = []
        temp = config.templates.copy()
        self.logging = logging

        for key, val in temp.items():
            self.sim_templates.update(val)

        nodes = list(config.data.nodes.data())

        for node in nodes:
            node_name = node[1]['data']['name']
            node_type = node[1]['data']['type']
            node_temp = self.sim_templates[node[1]['data']['template']].copy()

            if node_type == "QKDNode":
                node_in = QKDNode(
                    node_name,
                    self.timeline,
                    **node_temp
                )
            elif node_type == "Quantum_Router":
                mem = node_temp.pop('mem_type')
                mem_config = self.sim_templates[mem].copy()
                node_in = QuantumRouter(
                    node_name,
                    self.timeline,
                    **node_temp
                )
                for key, val in mem_config.items():
                    node_in.memory_array.update_memory_params(key, val)

            else:
                node = Node(node_name, self.timeline)

            self.topology.add_node(node_in)

        edges = list(config.data.edges.data())
        for edge in edges:
            edge_data = edge[2]['data'].copy()
            link_type = edge_data.pop('link_type')
            source = edge_data.pop('source')
            target = edge_data.pop('target')
            if link_type == 'Quantum':
                self.topology.add_quantum_connection(
                    source,
                    target,
                    **edge_data
                )
            else:
                self.topology.add_classical_connection(
                    source,
                    target,
                    **edge_data
                )

        labels = config.cc_delays.columns
        table = config.cc_delays.copy()

        table = table.to_numpy(dtype=int)

        for i in range(len(table)):
            for j in range(len(table[i])):
                if table[i][j] == 0:
                    continue
                delay = table[i][j] / 2
                cchannel_params = {"delay": delay, "distance": 1e3}
                self.topology.add_classical_channel(
                    labels[i],
                    labels[j],
                    **cchannel_params
                )

        bsm_hard = self.sim_templates['default_detector']
        for node in self.topology.get_nodes_by_type("BSMNode"):
            for key, val in bsm_hard.items():
                node.bsm.update_detectors_params(key, val)

        entanglement = self.sim_templates['default_entanglement']
        for node in self.topology.get_nodes_by_type("QuantumRouter"):
            node.network_manager.protocol_stack[1].set_swapping_success_rate(
                entanglement['succ_prob']
            )
            node.network_manager.protocol_stack[1].set_swapping_degradation(
                entanglement['degredation']
            )

        for node in self.topology.get_nodes_by_type("QuantumRouter"):
            table = self.topology.generate_forwarding_table(node.name)
            for dst, next_node in table.items():
                node.network_manager.protocol_stack[0].add_forwarding_rule(
                    dst,
                    next_node)

    def init_logging(self):
        set_logger(
            'sim_logging',
            self.timeline,
            DIRECTORY+'/'+self.sim_name+'_log.txt'
        )
        set_logger_level(self.logging)

    def random_request_simulation(self):

        # construct random request applications
        node_names = []
        for node in self.topology.get_nodes_by_type("QuantumRouter"):
            node_names.append(node.name)
        apps_new = []
        for i, name in enumerate(node_names):
            other_nodes = node_names[:]  # copy node name list
            other_nodes.remove(name)
            # create our application
            # arguments are the host node, possible destination node names,
            # and a seed for the random number generator.
            app = RandomRequestApp(self.topology.nodes[name], other_nodes, i)
            apps_new.append(app)
            app.start()

        self.apps = apps_new
        self.timeline.init()

    def getSimTime(self):
        tl = self.timeline
        ns = tl.convert_to_nanoseconds(tl.time)
        simulation_time = tl.ns_to_human_time(ns)

        if tl.stop_time == float('inf'):
            stop_time = 'NaN'
        else:
            ns = tl.convert_to_nanoseconds(tl.stop_time)
            stop_time = tl.ns_to_human_time(ns)
        new_simtime = f'{simulation_time} / {stop_time}'
        return new_simtime

    def write_to_file(self):
        tick = time.time()
        output = open(DIRECTORY+'/'+self.sim_name+'_results.txt', "w")
        output.write("execution time %.2f sec" % (time.time() - tick))

        for app in self.apps:
            output.write("node " + app.node.name+"\n")
            val = len(app.get_wait_time())
            output.write("\tnumber of wait times: %d" % val + '\n')
            wait = app.get_wait_time()
            wait_string = '['+' '.join(str(e) for e in wait)+']\n'
            output.write("\twait times: " + wait_string)
            reserve_string = '['+' '.join(str(e) for e in app.reserves)+']\n'
            output.write("\treservations: " + reserve_string)
            throughput = app.get_throughput()
            throughput_string = '['+' '.join(str(e) for e in throughput)+']\n'
            output.write("\tthroughput: " + throughput_string)

        output.write("Reservations Table:\n")
        node_names = []
        start_times = []
        end_times = []
        memory_sizes = []
        for node in self.topology.get_nodes_by_type("QuantumRouter"):
            node_name = node.name
            acc = node.network_manager.protocol_stack[1].accepted_reservation
            for reservation in acc:
                s_t, e_t, size = (
                    reservation.start_time,
                    reservation.end_time,
                    reservation.memory_size
                )
                cond_1 = reservation.initiator != node.name
                cond_2 = reservation.responder != node.name
                if(cond_1 and cond_2):
                    size *= 2
                node_names.append(node_name)
                start_times.append(s_t)
                end_times.append(e_t)
                memory_sizes.append(size)
        log = {
            "Node": node_names,
            "Start_time": start_times,
            "End_time": end_times,
            "Memory_size": memory_sizes
        }
        df = pd.DataFrame(log)
        output.write(df.to_string())
        output.close()
