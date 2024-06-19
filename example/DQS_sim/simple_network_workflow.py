from datetime import datetime
import json

from sequence_sim import run_sequence_simulation
from qutip_integration import final_purification, bell_dm, merge, gate_teleport


# meta params
CONFIG_FILE = "config_files/simulation_args.json"
NET_CONFIG_FILE = "config_files/topology_3_node.json"
OUTPUT_FILE = "results/simple_link_"+str(datetime.today())+".json"

# logging params
LOGGING = False
LOG_OUTPUT = "results/test_log.log"
MODULE_TO_LOG = ["timeline", "purification"]
VERBOSE_OUTPUT = False


# load config files
with open(CONFIG_FILE, 'r') as config:
    simulation_config = json.load(config)
with open(NET_CONFIG_FILE, 'r') as config:
    network_config = json.load(config)

cutoff_times = simulation_config["cutoff_times"]
num_trials = simulation_config["num_trials"]
prep_time = simulation_config["prep_time"]
app_info = simulation_config["applications"]

# set up storing data
data_dict = {
    "simulation config": simulation_config,
    "network config": network_config,
    "memory states": [],
    "memory entanglement": [],
    "memory entanglement time": []
}

for i, cutoff_time in enumerate(cutoff_times):
    print(f"Running {num_trials} trials for cutoff time {cutoff_time} s ({i + 1}/{len(cutoff_times)})")

    all_memory_states = []
    all_memory_entanglement = []
    all_memory_times = []

    for trial_no in range(num_trials):
        # run main SeQUeNCe simulation
        memory_states, memory_entanglement, memory_times = run_sequence_simulation(
            NET_CONFIG_FILE, prep_time, cutoff_time, app_info, trial_no
        )
        print(f"\tCompleted simulation trial {trial_no + 1}/{num_trials}")
        all_memory_states.append(memory_states)
        all_memory_entanglement.append(memory_entanglement)
        all_memory_times.append(memory_times)

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
