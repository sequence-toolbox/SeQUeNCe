from datetime import datetime
import json
import os
import argparse

import qutip

from sequence_sim import run_sequence_simulation
from qutip_integration import final_purification, merge, gate_teleport


def dqs_sim_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config',
        help='Simulation configuration file in JSON format'
    )
    parser.add_argument(
        'net_config',
        help='Network configuration file in JSON format'
    )
    parser.add_argument(
        '-o', '--output',
        default='results',
        help='Output path to dump results in. Default is \'results\''
    )
    return parser.parse_args()


# main simulation function
def dqs_sim(config_file, net_config_file, output_path, trial_no):
    # load config files
    with open(config_file, 'r') as config:
        simulation_config = json.load(config)
    with open(net_config_file, 'r') as config:
        network_config = json.load(config)

    # simulation parameters
    cutoff_time = simulation_config["cutoff_time"]

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

    # saving parameters
    qutip_filename = f"ghz_{trial_no}"


    # run main SeQUeNCe simulation
    memory_states, memory_entanglement, memory_times = run_sequence_simulation(
        net_config_file, prep_time, cutoff_time, app_info, trial_no
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
        ghz_filename = qutip_filename
        ghz_path = os.path.join(output_path, ghz_filename)
        qutip.qsave(ghz, name=ghz_path)

    # return trial data
    return_dict = {
        "initial entangled states": states,
        "purified states": states_purified,
        "GHZ state": ghz_filename
    }
    return return_dict


if __name__ == "__main__":
    args = dqs_sim_parser()

    # open config files
    with open(args.config, 'r') as config:
        simulation_config = json.load(config)
    with open(args.net_config, 'r') as config:
        network_config = json.load(config)

    # simulation params
    num_trials = simulation_config["num_trials"]
    num_other_nodes = len(simulation_config["applications"]["end_nodes"])

    # set up storing data (paths)
    now = datetime.now()
    output_subdir = f"dqs_sim_{now.strftime("%Y-%m-%d_%H%M%S")}"
    output_path = os.path.join(args.output, output_subdir)
    os.mkdir(output_path)
    main_results_file = os.path.join(output_path, "main.json")

    # data storage object
    data_dict = {
        "simulation config": simulation_config,
        "network config": network_config,
        "results": []
    }

    # main simulation loop
    print(f"Running {num_trials} trials for config '{args.config}' and topology '{args.net_config}'")
    results = []
    results_distribution = {"generated pairs": [0] * (num_other_nodes + 1),
                            "purified pairs": [0] * (num_other_nodes + 1),
                            "GHZ generated": 0}
    for trial_no in range(num_trials):
        trial_result = dqs_sim(args.config, args.net_config, output_path, trial_no)
        results.append(trial_result)

        # calculate trial distribution
        num_gen_pairs = len([node for node in trial_result["initial entangled states"]
                             if len(trial_result["initial entangled states"][node]) > 0])
        num_purified_pairs = len([node for node in trial_result["purified states"]
                                  if len(trial_result["purified states"][node]) > 0])
        results_distribution["generated pairs"][num_gen_pairs] += 1
        results_distribution["purified pairs"][num_purified_pairs] += 1
        if trial_result["GHZ state"]:
            results_distribution["GHZ generated"] += 1

        print(f"\tCompleted trial {trial_no + 1}/{num_trials}")

    print("Finished trials.")

    # save data for trials
    data_dict["results"] = results
    data_dict["results distribution"] = results_distribution

    # save output data
    with open(main_results_file, 'w') as fp:
        json.dump(data_dict, fp,
                  indent=4)
