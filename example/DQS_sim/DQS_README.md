# SeQUeNCE DQS Simulation Workflow

This small documentation file describes the setup of simulation scripts for the distributed quantum sensing project. In short, the workflow is as follows:

1. Generate or edit JSON configuration scripts to establish simulation parameters.
2. Run one of the two simulation scripts, which will invoke simulation in SeQUeNCe as well as perform final GHZ state generation.
3. View results, stored both in JSON format and in individual QuTiP `.qu` files.

Currently there is no way to automate sweeping over simulation parameters. However, this is easily achievable by using a script (in python, bash, etc.) to generate or edit the required config files.

## Configuration Files

The script requires two configuration files to run, both in JSON format. One contains parameters for the simulation and its protocols, while the other is the standard topology file for describing the physical simulation setup. Examples of each script may be viewed at `config_files/simulation_args.json` and `config_files/topology_3_node.json`, respectively.

For the simulation configuration file, the following keys are required:

* `num_trials`: How many simulation trials to run with the specified configuration.
* `prep_time`: Simulation time (in seconds) to allow for requests to propagate. This determines the start time for applications on the center node.
* `cutoff_time`: Simulation time (in seconds) to allow for entanglement generation. After this time, the SeQUeNCe simulation will end and the states will be saved.
* `applications`: Dictionary which determines application information for generating the desired GHZ state. This field contains three sub-keys:
	* `start_node`: name of the "center" node used for establishing the GHZ state.
	* `end_nodes`: name of each "spoke" node; at the end of simulation, a GHZ state will ideally be established between a memory on each of these end nodes.
	* `memory_number`: the number of memories to reserve for this request. If this is too large compared to available physical memories on each node, the request will be rejected and no states will be generated.
* `ghz_method`: Determines method of combining bipartite entanglement to generate the GHZ state. Must be one of `merge` or `gate_teleport`.

For the network configuration file, the standard format is used.

## Simulation Scripts

There are two simulation scripts available: `simple_network_workflow.py` and `parallel_simple_network_workflow.py`. Both scripts take the same arguments and run all trials for a specific configuration. The first script runs all of these trials sequentially, while the parallel script creates a process pool and assigns each trial to its own process.

The arguments for both scripts are as follows:

* `config`: path to simulation config JSON file.
* `net_config`: path to network conig JSON file.
* `-o` or `--output`: optional flag specifying the directory to save data in (relative to the current working directory). The default is `results`.

## Output Format

The output for each simulation will consist of a JSON file (titled `main.json`) and none to several files named `ghz_{i}.qu`. The JSON file summarizes the simulation parameters and results, as well as intermediate states generated during GHZ creation. The `.qu` files contain QuTiP objects describing the final density matrix.

When the simulation script is started, a subdirectory of the output path above will be created with the format `dqs_sim_{now.strftime("%Y-%m-%d_%H%M%S")}`, using the standard python datetime formatting with the current time. This subdirectory will contain the `main.json` file and qutip objects. For example, if a simulation is run on June 20 at 7:21 PM, the filestructure will appear as:

	results
	└ dqs_sim_2024-06-20_192100
	  ├ ghz_0.qu
	  ├ ghz_1.qu
	  │ ...
	  └ main.json

### JSON Structure

The JSON file contains 3 top-level keys:

* `simulation_config`: this field contains a copy of the simulation configuration used to generate the states.
* `network_config`: this field contains a copy of the network configuration used to generate the states.
* `results`: This field contains the simulation results. It is structured as a list, where the index is the trial number.

For each element of the `results` field, the results of a single trial are stored as a dictionary with the following keys:

* `initial entangled states`: this field stores all bipartite entanglement links generated at the end of simulation as a dictionary. The keys to this dictionary are the remote nodes (as described in the `applications -> end_nodes` field of the simulation config). The values in this dictionary are lists, where each element is itself a 4-element list describing the Bell diagonal state. 
* `purified states`: this field stores bipartite entanglement links with remote nodes after purification is performed as a dictionary. The keys are again the remote nodes, while the values are 4-element lists describing the Bell diagonal state. If the value is a 0-element list, the purification procedure was unsuccessful (or there were no initial states to purify).
* `GHZ state`: this field describes which `.qu` file stores the final GHZ state (as a QuTiP object). A value of `null` indicates that GHZ generation was not successful.

### QuTiP Objects

The density matrices for GHZ states generated by the simulation are in the fomrat of a QuTiP `qobj`. To save these, the native `qutip.qsave` method is used. To load the `qobj` into another python script, the `qutip.qload({filename})` method should be used, where `{filename}` specifies the desired `.qu` file. For example, consider the results of a specific trial in the `/path/to/results/main.json` file:

	results: {
		[
			{
				initial entangled states: {...},
				purified states: {...},
				GHZ state: "ghz_0"
			},
			...
		]
	}
	
To load the corresponding GHZ density matrix into another python script, the following code would be added:

	from qutip import qload
	
	ghz_state = qload("/path/to/results/ghz_0.qu")  # type(ghz_state) is qutip.Qobj