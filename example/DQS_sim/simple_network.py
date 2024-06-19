from datetime import datetime
import json

from ghz_app import GHZApp

from sequence.topology.router_net_topo import RouterNetTopo
import sequence.utils.log as log


# meta params
CONFIG_FILE = "config_files/topology_3_node.json"
OUTPUT_FILE = "results/simple_link_"+str(datetime.today())+".json"
LOGGING = True
LOG_OUTPUT = "results/test_log.log"
MODULE_TO_LOG = ["timeline", "purification"]
VERBOSE_OUTPUT = False

# simulation params
NUM_TRIALS = 10
PREP_TIME = 1  # units: s
cutoff_times = [10]  # unit: s

# qc params
QC_FREQ = 1e11

# application params
center_node_name = "center"
other_node_names = ["end1", "end2"]
NUM_MEMO = 10


# storing data
data_dict = {"cutoff times": cutoff_times,
             "preparation time": PREP_TIME,
             "application number of memories": NUM_MEMO,
             "number of trials": NUM_TRIALS,
             "memory states": [],
             "memory entanglement": [],
             "memory entanglement time": []}


for i, cutoff_time in enumerate(cutoff_times):
    print(f"Running {NUM_TRIALS} trials for cutoff time {cutoff_time} s ({i + 1}/{len(cutoff_times)})")

    all_memory_states = []
    all_memory_entanglement = []
    all_memory_times = []

    for trial_no in range(NUM_TRIALS):
        # establish network
        net_topo = RouterNetTopo(CONFIG_FILE)

        # timeline setup
        tl = net_topo.get_timeline()
        tl.stop_time = (PREP_TIME + cutoff_time) * 1e12
        # print(f"Simulation length: {tl.stop_time / 1e12} s")

        if LOGGING:
            # set log
            if i == 0:
                log.set_logger(__name__, tl, LOG_OUTPUT)
                log.set_logger_level('DEBUG')
                for module in MODULE_TO_LOG:
                    log.track_module(module)
            elif i == 1:
                for module in MODULE_TO_LOG:
                    log.remove_module(module)

        # network configuration
        routers = net_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
        bsm_nodes = net_topo.get_nodes_by_type(RouterNetTopo.BSM_NODE)

        for j, node in enumerate(routers + bsm_nodes):
            node.set_seed(j + (trial_no * 3))

        # set quantum channel parameters
        for qc in net_topo.get_qchannels():
            qc.frequency = QC_FREQ

        # establish apps on the center node
        start_node = None
        for node in routers:
            if node.name == center_node_name:
                start_node = node
                break
        if not start_node:
            raise ValueError(f"Invalid app node name {center_node_name}")

        apps = [GHZApp(start_node) for _ in other_node_names]

        # initialize and start apps
        tl.init()

        for app, other_node in zip(apps, other_node_names):
            app.start(other_node, PREP_TIME*1e12, (PREP_TIME + cutoff_time)*1e12, NUM_MEMO, fidelity=1.0)

        tl.run()

        print(f"\tCompleted trial {trial_no + 1}/{NUM_TRIALS}")

        # save data for trial
        memory_states = []
        memory_entanglement = []
        memory_times = []

        memo_arr = start_node.get_components_by_type("MemoryArray")[0]
        for index in apps[1].memo_to_reserve:  # iterate through memo indices
            memo = memo_arr[index]
            update_time = memo.last_update_time
            state = memo.get_bds_state()
            remote = memo.entangled_memory['node_id']
            if remote is not None:
                memory_states.append(list(state))  # ndarray not serializable for JSON
                memory_entanglement.append(remote)
                memory_times.append(update_time)

        all_memory_states.append(memory_states)
        all_memory_entanglement.append(memory_entanglement)
        all_memory_times.append(memory_times)

        if VERBOSE_OUTPUT:
            print("\tMemory states:")
            for index in apps[1].memo_to_reserve:  # iterate through memo indices
                memo = memo_arr[index]
                # state = tl.quantum_manager.get(memo.qstate_key).state
                update_time = memo.last_update_time
                state = memo.get_bds_state()
                remote = memo.entangled_memory['node_id']
                print(f"\t\t{index}: {memo} ({remote})")
                print(f"\t\t\t{state}")
                print(f"\t\t\tUpdate time: {update_time * 1e-12} s")
                print(f"\t\t\tGeneration time: {memo.generation_time * 1e-12} s")

    print("Finished trials.")

    # save data for current cutoff time
    data_dict["memory states"].append(all_memory_states)
    data_dict["memory entanglement"].append(all_memory_entanglement)
    data_dict["memory entanglement time"].append(all_memory_times)

print("Finished data collection.")

# save output data
with open(OUTPUT_FILE, 'w') as fp:
    json.dump(data_dict, fp,
              indent=4)
