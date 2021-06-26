"""
A Class which serves as the interface between the SeQUeNCe simulator
and GUI components
"""

import time, os
import pandas as pd
import sequence.topology.node as seq_node
from sequence.kernel.timeline import Timeline
from sequence.topology.topology import Topology
from sequence.app.random_request import RandomRequestApp

class gui_sim():
    def __init__(self, sim_time:int, time_scale:int, sim_name, config):
        self.sim_name=sim_name
        self.timeline = Timeline(sim_time * time_scale)
        self.timeline.seed(0)
        self.topology = Topology(sim_name, self.timeline)
        
        nodes = list(config.data.nodes.data())

        for node in nodes:
            node_name = node[1]['data']['name']
            node_type = node[1]['data']['type']
            node_temp = config.templates[node[1]['data']['template']].copy()
            
            if node_type == "QKDNode":
                node_in = seq_node.QKDNode(node_name, self.timeline, **node_temp)
            elif node_type == "Quantum_Router":
                mem_config = config.templates[node_temp.pop('mem_type')].copy()
                node_in = seq_node.QuantumRouter(node_name, self.timeline, **node_temp)
                for key, val in mem_config.items():
                    node_in.memory_array.update_memory_params(key, val)
                
            else:
                node = seq_node.Node(node_name, self.timeline)
            
            self.topology.add_node(node_in)

        edges = list(config.data.edges.data())
        for edge in edges:
            edge_data = edge[2]['data'].copy()
            link_type = edge_data.pop('link_type')
            source=edge_data.pop('source')
            target=edge_data.pop('target')
            if(link_type=='Quantum'):
                self.topology.add_quantum_connection(source, target, **edge_data)
            else:
                self.topology.add_classical_connection(source, target, **edge_data)

        labels = config.net_delay_times.columns[1:]
        table = config.net_delay_times
        table = table.drop(['To'], axis=1)

        table = table.to_numpy(dtype=int)

        for i in range(len(table)):
            for j in range(len(table[i])):
                if table[i][j] == 0:
                    continue
                delay = table[i][j] / 2
                cchannel_params = {"delay": delay, "distance": 1e3}
                self.topology.add_classical_channel(labels[i], labels[j], **cchannel_params)

        bsm_hard = config.templates['default_detector']
        for node in self.topology.get_nodes_by_type("BSMNode"):
            for key, val in bsm_hard.items():
                node.bsm.update_detectors_params(key, val)

        entanglement = config.templates['default_entanglement']
        for node in self.topology.get_nodes_by_type("QuantumRouter"):
            node.network_manager.protocol_stack[1].set_swapping_success_rate(entanglement['succ_prob'])
            node.network_manager.protocol_stack[1].set_swapping_degradation(entanglement['degredation'])

        for node in self.topology.get_nodes_by_type("QuantumRouter"):
            table = self.topology.generate_forwarding_table(node.name)
            for dst, next_node in table.items():
                node.network_manager.protocol_stack[0].add_forwarding_rule(dst, next_node)

    def random_request_simulation(self):
        
        # construct random request applications
        node_names = [node.name for node in self.topology.get_nodes_by_type("QuantumRouter")]
        apps = []
        for i, name in enumerate(node_names):
            other_nodes = node_names[:] # copy node name list
            other_nodes.remove(name)
            # create our application
            # arguments are the host node, possible destination node names, and a seed for the random number generator.
            app = RandomRequestApp(self.topology.nodes[name], other_nodes, i)
            apps.append(app)
            app.start()
            
        self.timeline.init()
        tick = time.time()
        self.timeline.run()

        output = open(os.path.split(__file__)[0]+'/'+self.sim_name+'.txt', "w")

        output.write("execution time %.2f sec" % (time.time() - tick))
        
        for app in apps:
            output.write("node " + app.node.name+"\n")
            output.write("\tnumber of wait times: %d" % len(app.get_wait_time())+'\n')
            wait_string = '['+' '.join(str(e) for e in app.get_wait_time())+']\n'
            output.write("\twait times: " + wait_string)
            reserve_string = '['+' '.join(str(e) for e in app.reserves)+']\n'
            output.write("\treservations: " + reserve_string)
            throughput_string = '['+' '.join(str(e) for e in app.get_throughput())+']\n'
            output.write("\tthroughput: " +throughput_string)
        
        output.write("Reservations Table:\n")
        node_names = []
        start_times = []
        end_times = []
        memory_sizes = []
        for node in self.topology.get_nodes_by_type("QuantumRouter"):
            node_name = node.name
            for reservation in node.network_manager.protocol_stack[1].accepted_reservation:
                s_t, e_t, size = reservation.start_time, reservation.end_time, reservation.memory_size
                if reservation.initiator != node.name and reservation.responder != node.name:
                    size *= 2
                node_names.append(node_name)
                start_times.append(s_t)
                end_times.append(e_t)
                memory_sizes.append(size)
        log = {"Node": node_names, "Start_time": start_times, "End_time": end_times, "Memory_size": memory_sizes}
        df = pd.DataFrame(log)
        output.write(df.to_string())
        output.close()