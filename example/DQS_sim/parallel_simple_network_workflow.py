from datetime import datetime
import json
import os
import multiprocessing
from itertools import repeat
import time
import numpy as np

from simple_network_workflow import dqs_sim, dqs_sim_parser


def multiprocess_helper(l, f, trial_start, num_trials, *args):
    for trial in range(trial_start, trial_start+num_trials):
        res = f(*args, trial_no=trial)
        l.append(res)


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

    # setup for multiprocessing
    manager = multiprocessing.Manager()
    results = manager.list()

    num_processes = multiprocessing.cpu_count()
    trials_per_process = num_trials // num_processes
    extra = num_trials % num_processes
    split_trials = trials_per_process * np.ones(num_processes, dtype=int)
    split_trials[0:extra] += 1
    trial_start = np.cumsum(split_trials) - split_trials

    # run trials in parallel
    print(f"Running {num_trials} trials for config '{args.config}' and topology '{args.net_config}'")
    print(f"Number of processes: {num_processes}")
    tick = time.time()

    with multiprocessing.Pool(processes=num_processes) as pool:
        async_res = pool.starmap_async(multiprocess_helper,
                                       zip(repeat(results),
                                           repeat(dqs_sim),
                                           trial_start,
                                           split_trials,
                                           repeat(args.config),
                                           repeat(args.net_config),
                                           repeat(output_path)))

        while not async_res.ready():
            time.sleep(1)
            num_finished = len(results)
            print(f"\tCompleted {num_finished}/{num_trials} trials ({num_finished/num_trials:.0%})")

    # calculate trial distributions
    print("Calculating distributions...")
    results_distribution = {"generated pairs": [0] * (num_other_nodes + 1),
                            "purified pairs": [0] * (num_other_nodes + 1),
                            "GHZ generated": 0}
    for trial_result in results:
        num_gen_pairs = len([node for node in trial_result["initial entangled states"]
                             if len(trial_result["initial entangled states"][node]) > 0])
        num_purified_pairs = len([node for node in trial_result["purified states"]
                                  if len(trial_result["purified states"][node]) > 0])
        results_distribution["generated pairs"][num_gen_pairs] += 1
        results_distribution["purified pairs"][num_purified_pairs] += 1
        if trial_result["GHZ state"]:
            results_distribution["GHZ generated"] += 1

    print("Finished simulation.")
    total_time = time.time() - tick
    print(f"Runtime: {total_time:.3f}s")

    # save data for trials
    data_dict["results"] = list(results)
    data_dict["results distribution"] = results_distribution

    # save output data
    with open(main_results_file, 'w') as fp:
        json.dump(data_dict, fp,
                  indent=4)
