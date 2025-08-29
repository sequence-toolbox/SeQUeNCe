import numpy as np
import pandas as pd

from build.lib.sequence.constants import DENSITY_MATRIX_FORMALISM
from sequence.app.request_app import RequestApp
from sequence.constants import KET_STATE_FORMALISM, SINGLE_HERALDED
from sequence.entanglement_management.purification import BBPSSWMessage
from sequence.kernel.quantum_manager import QuantumManager
from sequence.entanglement_management.generation.generation import EntanglementGenerationA, EntanglementGenerationB
from sequence.entanglement_management.purification.bbpssw_protocol import BBPSSWProtocol
from sequence.entanglement_management.purification.bbpssw_circuit import BBPSSWCircuit
from sequence.entanglement_management.purification.bbpssw_bds import BBPSSW_BDS
from sequence.topology.node import QuantumRouter
from sequence.topology.router_net_topo import RouterNetTopo

"""
This replicates the experiment Fig.6 https://arxiv.org/pdf/2504.01290

Author: R. J. Hayek, Argonne National Laboratory
"""
import json
import multiprocessing as mp
import os
import time

@BBPSSWProtocol.register('tracking')
class TrackingBBPSWProtocol(BBPSSW_BDS):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        self.owner.ep_count += 1
        if self.meas_res == msg.meas_res:
            self.owner.ep_success += 1
            self.owner.new_fid = self.kept_memo.fidelity
        if self.owner.ep_success == 500:
            self.owner.time_to_ep = self.owner.timeline.now() - 1e12

        super().received_message(src, msg)

    def start(self):
        self.owner.ep_count += 1
        super().start()


def bananas():
    _original_init = QuantumRouter.__init__
    def _patched_init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        self.successful_attempts = 0
        self.total_attempts = 0
        self.time_to_thousand = 0
        self.ep_count = 0
        self.ep_success = 0
        self.time_to_ep = 0
        self.new_fid = 0.0
    QuantumRouter.__init__ = _patched_init

    # Patch EntanglementGenerationA to track entanglement generation attempts
    _original_entanglement_succeed = EntanglementGenerationA._entanglement_succeed
    def _patched_entanglement_succeed(self):
        self.owner.total_attempts += 1
        self.owner.successful_attempts += 1
        if self.owner.successful_attempts == 1000:
            self.owner.time_to_thousand = self.owner.timeline.now() - 1e12
        return _original_entanglement_succeed(self)
    EntanglementGenerationA._entanglement_succeed = _patched_entanglement_succeed

    _original_entanglement_fail = EntanglementGenerationA._entanglement_fail
    def _patched_entanglement_fail(self):
        self.owner.total_attempts += 1
        return _original_entanglement_fail(self)
    EntanglementGenerationA._entanglement_fail = _patched_entanglement_fail

def _run_trial(CONFIG_FILE, PREP_TIME, COLLECT_TIME, QC_FREQ, APP_NODE_NAME,
               OTHER_NODE_NAME, NUM_MEMORIES, fidelity, trial) -> tuple:
    bananas()
    # establish network
    QuantumManager.set_global_manager_formalism(DENSITY_MATRIX_FORMALISM)
    EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    BBPSSWProtocol.set_formalism('tracking')
    net_topo = RouterNetTopo(CONFIG_FILE)

    # timeline setup
    tl = net_topo.get_timeline()
    tl.stop_time = PREP_TIME + COLLECT_TIME

    # network configuration
    routers = net_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    bsm_nodes = net_topo.get_nodes_by_type(RouterNetTopo.BSM_NODE)

    base_seed = int(time.time_ns()) % (2 ** 20) + os.getpid()
    # Random seed for performing the simulations
    for j, node in enumerate(routers + bsm_nodes):
        node.set_seed(base_seed + trial * 1000 + j)

    # set quantum channel parameters
    for qc in net_topo.get_qchannels():
        qc.frequency = QC_FREQ

    # establish "left" node as the start node.
    start_node = None
    for node in routers:
        if node.name == APP_NODE_NAME:
            start_node = node
            break
    # Checking to see if the start node was established or not
    if not start_node:
        raise ValueError(f"Invalid app node name {APP_NODE_NAME}")

    # Setting the "right" node as the 'end' node
    end_node = None
    for node in routers:
        if node.name == OTHER_NODE_NAME:
            end_node = node
            break
    # Checking to see if the end node was established or not
    if not start_node:
        raise ValueError(f"Invalid other node name {OTHER_NODE_NAME}")

    # Establishing the apps on the start and end nodes.
    app_start = RequestApp(start_node)
    RequestApp(end_node)  # This call is NECESSARY, though unassigned

    # initialize and start app
    tl.init()
    app_start.start(OTHER_NODE_NAME, PREP_TIME, PREP_TIME + COLLECT_TIME, NUM_MEMORIES, 0.01)
    tl.run()

    # Used for debugging
    attempt = app_start.node.total_attempts
    success = app_start.node.successful_attempts
    print(f'Attempts: {attempt}')
    print(f'Success: {success}')
    #success_rate = app_start.node.ep_success / app_start.node.ep_count
    #print('Success rate:', success_rate)

    #final_fidelity = app_start.node.new_fid
    #print(final_fidelity)

    return attempt


def modify_config(config_file, decoherence, fidelity):
    """
    Modify the configuration file to set decoherence and initial fidelity.
    """
    with open(config_file, 'r') as file:
        config = json.load(file)

    config['templates']['perfect_router']['MemoryArray']['coherence_time'] = decoherence
    config['templates']['perfect_router']['MemoryArray']['fidelity'] = fidelity

    with open(config_file, 'w') as file:
        json.dump(config, file, indent=4)


def main():
    bananas()  # Monkey patch to track attempts and successes
    print("Starting the experiment.")
    CONFIG_FILE = "ep_config.json"

    NO_TRIALS = 10

    # simulation params
    NUM_MEMORIES = 2
    PREP_TIME = int(1e12)  # 1 second
    COLLECT_TIME = int(10e12) / NUM_MEMORIES  # 10 seconds

    # qc params
    QC_FREQ = 1e11

    # application params
    APP_NODE_NAME = "left"
    OTHER_NODE_NAME = "right"


    data_dict = {
        'Average EG Time': [],
        'Average Success Rate': [],
    }

    print(f"Running {NO_TRIALS} trials")

    _run_trial(CONFIG_FILE, PREP_TIME, COLLECT_TIME, QC_FREQ, APP_NODE_NAME,
        OTHER_NODE_NAME, NUM_MEMORIES, 1, 1)



    print('Experiment completed. Saving results to CSV.')
    df = pd.DataFrame(data_dict)
    df.to_csv(f'experiment_results_{NO_TRIALS}_minfid.csv', index=False)

if __name__ == "__main__":
    main()