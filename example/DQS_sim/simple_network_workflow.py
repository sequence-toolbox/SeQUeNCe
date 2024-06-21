from datetime import datetime
import json
import os

import qutip

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
cutoff_time = simulation_config["cutoff_time"]
num_trials = simulation_config["num_trials"]
prep_time = simulation_config["prep_time"]
app_info = simulation_config["applications"]
ghz_method = simulation_config["ghz_method"]
assert ghz_method in ["merge", "gate_teleport"], \
    f"invalid GHZ generation method {ghz_method} (must be 'merge' or 'gate_teleport'"

# purification/GHZ parameters
center_node = app_info["start_node"]
other_nodes = app_info["end_nodes"]
gate_fid = {node["name"]: node["gate_fidelity"] for node in network_config["nodes"]}
meas_fid = {node["name"]: node["measurement_fidelity"] for node in network_config["nodes"]}
if len(other_nodes) > 2:
    raise NotImplementedError("case for greater than 2 remote nodes not yet implemented")

# set up storing data (paths)
now = datetime.now()
output_subdir = f"dqs_sim_{now.strftime("%Y-%m-%d_%H%M%S")}"
output_path = os.path.join(OUTPUT_DIR, output_subdir)
os.mkdir(output_path)
main_results_file = os.path.join(output_path, "main.json")
qutip_storage_count = 0  # for giving each qutip obj a unique filename
qutip_template = "ghz_{}"

# data sotrage object
data_dict = {
    "simulation config": simulation_config,
    "network config": network_config,
    "results": []
}


# main simulation loop
print(f"Running {num_trials} trials for config '{CONFIG_FILE}' and topology '{NET_CONFIG_FILE}'")
results = []
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
    successful_purification = [len(states_purified[node]) > 0 for node in other_nodes]
    ghz_filename = None
    if all(successful_purification):
        # generate GHZ
        if ghz_method == "merge":
            ghz = merge(*states_purified.values(), gate_fid[center_node], meas_fid[center_node])
        else:
            ghz = gate_teleport(*states_purified.values(), gate_fid[center_node], meas_fid[center_node])

        # save qutip obj
        ghz_filename = qutip_template.format(qutip_storage_count)
        ghz_path = os.path.join(output_path, ghz_filename)
        qutip.qsave(ghz, name=ghz_path)
        qutip_storage_count += 1

    # save trial data
    results.append({
        "initial entangled states": states,
        "purified states": states_purified,
        "GHZ state": ghz_filename
    })

    print(f"\tCompleted trial {trial_no + 1}/{num_trials}")

print("Finished trials.")

# save data for current cutoff time
data_dict["results"] = results


# save output data
with open(main_results_file, 'w') as fp:
    json.dump(data_dict, fp,
              indent=4)
