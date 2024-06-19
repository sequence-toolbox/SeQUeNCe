from datetime import datetime
import json
import os

from sequence_sim import run_sequence_simulation
from qutip_integration import final_purification, bell_dm, merge, gate_teleport


# meta params
CONFIG_FILE = "config_files/simulation_args.json"
NET_CONFIG_FILE = "config_files/topology_3_node.json"
OUTPUT_DIR = "results"

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

# simulation parameters
cutoff_times = simulation_config["cutoff_times"]
num_trials = simulation_config["num_trials"]
prep_time = simulation_config["prep_time"]
app_info = simulation_config["applications"]

# purification/GHZ parameters
center_node = app_info["start_node"]
other_nodes = app_info["end_nodes"]
gate_fid = {node["name"]: node["gate_fidelity"] for node in network_config["nodes"]}
meas_fid = {node["name"]: node["measurement_fidelity"] for node in network_config["nodes"]}

# set up storing data
now = datetime.now()
output_file = f"dqs_sim_{now.strftime("%Y-%m-%d_%H%M%S")}.json"
output_path = os.path.join(OUTPUT_DIR, output_file)
data_dict = {
    "simulation config": simulation_config,
    "network config": network_config,
    "results": []
}

for i, cutoff_time in enumerate(cutoff_times):
    print(f"Running {num_trials} trials for cutoff time {cutoff_time} s ({i + 1}/{len(cutoff_times)})")

    results_all_trials = []

    for trial_no in range(num_trials):

        # run main SeQUeNCe simulation
        memory_states, memory_entanglement, memory_times = run_sequence_simulation(
            NET_CONFIG_FILE, prep_time, cutoff_time, app_info, trial_no
        )

        # compile memory info
        states = {name: [] for name in other_nodes}
        for state, other in zip(memory_states, memory_entanglement):
            states[other].append(state)

        # run purification
        states_purified = {}
        gate_fid_1 = gate_fid[center_node]
        meas_fid_1 = meas_fid[center_node]
        for end_node in other_nodes:
            purified_state = final_purification(
                states[end_node],
                gate_fid_1,
                gate_fid[end_node],
                meas_fid_1,
                meas_fid[end_node]
            )
            states_purified[end_node] = purified_state

        # run GHZ generation (if necessary)

        # save trial data
        results_all_trials.append({
            "initial entangled states": states,
            "purified states": states_purified
        })

        print(f"\tCompleted trial {trial_no + 1}/{num_trials}")

    print("Finished trials.")

    # save data for current cutoff time
    data_dict["results"].append(results_all_trials)

print("Finished data collection.")

# save output data
with open(output_path, 'w') as fp:
    json.dump(data_dict, fp,
              indent=4)
