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
from ..topology.router_net_topo import RouterNetTopo
from ..app.random_request import RandomRequestApp
from ..utils.log import *

DIRECTORY, _ = os.path.split(__file__)


class GuiSimulator:
    def __init__(self, sim_time: int, time_scale: int, logging: str, sim_name, config):
        self.sim_time = sim_time
        self.time_scale = time_scale
        self.sim_name = sim_name
        self.apps = []
        self.logging = logging

        # set up timeline with proper time
        total_runtime = sim_time * time_scale
        config[Topology.STOP_TIME] = total_runtime
        self.topology = RouterNetTopo(config)
        self.timeline = self.topology.get_timeline()

    def init_logging(self):
        set_logger(
            'sim_logging',
            self.timeline,
            DIRECTORY+'/'+self.sim_name+'_log.txt'
        )
        set_logger_level(self.logging)

    def random_request_simulation(self):
        # construct random request applications
        nodes = self.topology.get_nodes_by_type("QuantumRouter")
        node_names = []
        for node in nodes:
            node_names.append(node.name)
        apps_new = []
        for i, (name, node) in enumerate(zip(node_names, nodes)):
            # TODO: Add in more arguments through GUI
            min_dur = int(10e12)  # 10 seconds
            max_dur = int(20e12)  # 20 seconds
            memory_array = node.get_components_by_type('MemoryArray')[0]
            min_size = 1
            max_size = len(memory_array) // 2
            min_fidelity = 0.8
            max_fidelity = 1

            other_nodes = node_names[:]  # copy node name list
            other_nodes.remove(name)
            # create our application
            app = RandomRequestApp(node, other_nodes, i,
                                   min_dur, max_dur,
                                   min_size, max_size,
                                   min_fidelity, max_fidelity)
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
        output_filename = os.path.join(DIRECTORY, self.sim_name+'_results.txt')

        with open(output_filename, "w") as output:
            output.write("execution time %.2f sec" % (time.time() - tick) + '\n')

            for app in self.apps:
                output.write("node " + app.node.name + "\n")
                val = len(app.get_wait_time())
                output.write("\tnumber of wait times: %d" % val + '\n')
                wait = app.get_wait_time()
                wait_string = '[' + ' '.join(str(e) for e in wait) + ']\n'
                output.write("\twait times: " + wait_string)
                reserve_string = '[' + ' '.join(str(e) for e in app.reserves) + ']\n'
                output.write("\treservations: " + reserve_string)
                throughput = app.get_throughput()
                output.write("\tthroughput: " + str(throughput) + '\n')

            output.write("Reservations Table:\n")
            node_names = []
            start_times = []
            end_times = []
            memory_sizes = []
            for node in self.topology.get_nodes_by_type("QuantumRouter"):
                node_name = node.name
                acc = node.network_manager.protocol_stack[1].accepted_reservations
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
