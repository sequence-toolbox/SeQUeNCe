from datetime import datetime
import json
import os
import multiprocessing
from itertools import repeat

from simple_network_workflow import dqs_sim


if __name__ == "__main__":
    # meta params
    CONFIG_FILE = "config_files/simulation_args.json"
    NET_CONFIG_FILE = "config_files/topology_3_node.json"
    OUTPUT_DIR = "results"

    # logging params
    LOGGING = False
    LOG_OUTPUT = "results/test_log.log"
    MODULE_TO_LOG = ["timeline", "purification"]
    VERBOSE_OUTPUT = False

    # open config files
    with open(CONFIG_FILE, 'r') as config:
        simulation_config = json.load(config)
    with open(NET_CONFIG_FILE, 'r') as config:
        network_config = json.load(config)

    # simulation params
    num_trials = simulation_config["num_trials"]

    # set up storing data (paths)
    now = datetime.now()
    output_subdir = f"dqs_sim_{now.strftime("%Y-%m-%d_%H%M%S")}"
    output_path = os.path.join(OUTPUT_DIR, output_subdir)
    os.mkdir(output_path)
    main_results_file = os.path.join(output_path, "main.json")

    # data storage object
    data_dict = {
        "simulation config": simulation_config,
        "network config": network_config,
        "results": []
    }

    # main simulation loop
    print(f"Running {num_trials} trials for config '{CONFIG_FILE}' and topology '{NET_CONFIG_FILE}'")
    with multiprocessing.Pool(processes=num_trials) as pool:
        results = pool.starmap(dqs_sim, zip(repeat(CONFIG_FILE),
                                            repeat(NET_CONFIG_FILE),
                                            repeat(output_path),
                                            range(num_trials)))

    print("Finished trials.")

    # save data for trials
    data_dict["results"] = results

    # save output data
    with open(main_results_file, 'w') as fp:
        json.dump(data_dict, fp,
                  indent=4)
