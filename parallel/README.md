# SeQUeNCe Parallel Simulation Tools

This directory contains resources for running simulations using parallel processing. As mentioned in our paper (TODO: add link), SeQUeNCe is able to simulate portions of a network as different processes, where shared quantum states are tracked by a Quantum Manager Server running as a separate program. For details on how to set up and run parallel simulatoins with SeQUeNCe, please visit the [documentation page](https://sequence-toolbox.github.io/).

## Installing
Installation of SeQUeNCe includes the necessary simulation tools to run parallel simulations. On top of this, an installation of an MPI implementation is required. Additionally, if the C++ version of the Quantum Manager Server is used (see the next section), an installation of CMake and the Eigen library is required.

### MPI

### CMake

### Eigen

## Quantum Manager Server
Before running a parallel simulation script, a quantum manager server must be started to service requests from the simulation clients. SeQUeNCe includes a server program written in Python for ease of use and customization, as well as a version written in C++ for improved performance. Both programs communicate with the simulation clients using sockets. A description of how to run the server can be found on the [documentation page](https://sequence-toolbox.github.io/).

### C++ Server Build
SeQUeNCe uses CMake to ease the compilation of the quantum manager server files. To install, first navigate to the cpp\_server directory and create a build directory:
```
$ cd cpp_server
$ mkdir cpp_server_build
```
Next, use CMake to configure the project and generate makefiles:
```
$ cd cpp_server_build
$ cmake ..
```
And finally, build the executable for the Quantum Manager Server:
```
$ cmake --build . --target quantum_server_cpp
```
To build additional executables used for testing, omit the `--target quantum_server_cpp` specification from the above command.

## Usage Examples
Examples of how to set up and run parallel simulations are found in the examples directory.
