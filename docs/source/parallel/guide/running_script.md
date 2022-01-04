# Guide: Running a Parallel Script

## JSON Format
A few additions will need to be made to the JSON file to designate a simulation as parallel and facilitate proper allocation of resources. As usual, the name of each field in the JSON is defined by a variable in the `Topology` class or one of its subclasses. For this guide, the `RouterNetTopo` class will be used (such that variable `VAR` refers to `RouterNetTopo.VAR`).

First, the general parallel settings will need to be listed in the JSON. The variable name for each setting is listed first, followed by the default string value.
- `IS_PARALLEL` (default `“is_parallel”`) should be set to true; if omitted or set to false, further settings will be ignored.
- `PROC_NUM` (default `“process_num”`) should be set to the desired number of processes for the simulation. If this differs from the MPI size at runtime, an assertion error will be raised.
- `IP` (default `“ip”`) should be set to the IP address of the quantum manager server; if run on the same machine, set to `“127.0.0.1”`.
- `PORT` (default `“port”`) should be set to the port the quantum manager server will be listening on. The `get_port.py` script may be used to find an available port.
- `LOOKAHEAD` (default `“lookahead”`) should be set to the lookahead time (in picoseconds of simulation time).

Finally, we will add a subfield to each node describing which process this node should belong to. The name of this field is `GROUP` (default `“group”`) and the process should be an integer referring to a specific (zero-indexed) process.

Putting all of this together, an example JSON is shown below:
```
{
    "nodes": [
        {
            "name": "router_0",
            "type": "QuantumRouter",
            "seed": 0,
            "memo_size": 100,
            "group": 0
        },
        ...
        {
            "name": "router_7",
            "type": "QuantumRouter",
            "seed": 0,
            "memo_size": 100,
            "group": 7
        }
    ],
    "qconnections": [
        ...
    ],
    "cchannels": [
        ...
    ],
    "stop_time": Infinity,
    "is_parallel": true,
    "process_num": 8,
    "ip": "127.0.0.1",
    "port": 6789,
    "lookahead": 2500000,
    "groups": [
        {
            "type": "sync"
        },
        ...
        {
            "type": "sync"
        }
    ]
}
```

## Parallel Script Modifications
If a JSON file is being used to set up the simulation network, all that is required for a simulation script is that the method `ParallelTimeline.quantum_manager.disconnect_from_server()` is called after timeline execution finishes. This function closes the socket communication with the server, and allows the server program to record metrics and close once all clients have disconnected. Optionally, additional parallel performance metrics may be added to the script, as described below.

### Additional Parallel Simulation Metrics
In addition to the usual metrics, parallel timelines collect a series of metrics relating to parallel simulation. These are:
- `sync_counter`: a count of the number of synchronization events between timelines
- `exchange_counter`: a count of the number of cross-timeline events scheduled on the specific parallel timeline
- `computing_time`: wall clock time during which the timeline was executing local events
- `communication_time`: wall clock time during which the timeline was performing synchronization with other timelines.

After simulation has completed, these fields may be read out from a parallel timeline object.

Additionally, the Python version of the quantum manager server collects some metrics relating to its operation and will output these to a csv file:
- `msg_counter`: a count of the total number of messages received by the server
- `traffic_counter`: a count of the total number of message packets received by the server
- `{message_type}_timer`: wall-clock time of computation time for each message type

The next section contains information about how to specify the destination file for these metrics.

### Simulations with No JSON Configuration File
If it is required to run a simulation with no input JSON file for network configuration, additional steps should be taken to ensure that the parallel timelines and simulation objects are set up correctly.
1. Determine a scheme for allocating nodes to processes, and write a function that can determine the process a node should belong to by name during runtime:
    ```python
    def name_to_proc(name: str) -> int:
        # insert code here
    ```
1. Within the script, utilize the mpi rank and size to determine the number of processes and the id of the current process, respectively:
    ```python
    from mpi4py import MPI

    mpi_rank = MPI.COMM_WORLD.Get_rank()
    mpi_size = MPI.COMM_WORLD.Get_size()
    ```
1. Create a parallel timeline instance for the current process:
    ```python
    from sequence.kernel.p_timeline import ParallelTimeline
   
    p_tl = ParallelTimeline(...)
    ```
1. When creating nodes, only create a node object for nodes that are on the current process (the MPI rank). If a node is not on the current process, add to the `ParallelTimeline.foreign_entities` dictionary with the key being the node name and the value being the id of the process containing the node:
    ```python
    list_of_names = [...] # list of names for all nodes in the network
    local_nodes = []

    for node_name in list_of_names:
        proc = name_to_proc(node_name)
        if proc == mpi_rank:
            node = QuantumRouter(node_name, p_tl, *args)
            local_nodes.append(node)
        else:
            p_tl.foreign_entities[node_name] = proc
    ```
1. When creating quantum and classical channel links, only generate links where the source node is on the current process. If the destination node is on a different process, use the name of the foreign node as the receiver as usual.
1. Include a call to `ParallelTimeline.quantum_manager.disconnect_from_server()`, as mentioned previously.

These steps will ensure the proper connectivity of the network without breaks or redundant network elements.

## Running Scripts and the Quantum Manager Server

### Python Version
To run the Quantum Manager Server in Python with a default configuration, the `qm_server.py` script has been provided. This script takes three arguments:
- `ip`: the IP address the server should use
- `port`: the port the server should connect to and listen on
- `client_num`: the number of quantum manager clients that will connect to the serve (this is the same as the number of MPI processes used for executing the desired simulation script).

The default configuration includes using Ket vectors for storing quantum state information and writing the server output to the file `server_log.json`. If these parameters need to be changed, a script should be written that directly calls the `start_server` function of the `src.kernel.quantum_manager_server` module with the desired arguments (or the default `qm_server.py` file modified to do so).

### C++ Version
To run the Quantum Manager Server written in C++, first compile and build the server as described in the parallel simulation prerequisites and Installation page. The server may then be run as an executable with the following args:
- `ip`: the IP address the server should use
- `port`: the port the server should connect to and listen on
- `client_num`: the number of quantum manager clients that will connect to the serve (this is the same as the number of MPI processes used for executing the desired simulation script).
- `formalism`: the formalism to use for storing quantum states (so far, only Ket vectors are implemented and this field is ignored).
- `log_file`: the output file for Quantum Manager Server log information.

### Simulation Scripts
Simulation scripts themselves should be run as a separate program using the `mpiexec` command. The `-n` flag may be used to specify the number of processes to use for simulation. After this, the `python` or `python3` command should be entered in the usual manner to run the script:
```
$ mpiexec -n 2 python3 my_script.py [args]
```
Note that the Quantum Manager Server program should be started before the simulation script. Additionally, it should be confirmed that the following parameters match between the Quantum Manager Server and the individual script:
- The number of MPI processes used should match the `client_num` parameter for the server.
- The server IP and port written into the simulation script should match the parameters of the server.
- The formalism used for the parallel timelines should match that used for the server.
    - The default formalism generated by using a JSON configuration file is to use ket vectors, and this is currently the only implemented formalism for the C++ server.

