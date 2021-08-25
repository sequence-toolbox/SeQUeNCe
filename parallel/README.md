# SeQUeNCe Parallel Simulation Tools

This directory contains resources for running simulations using parallel processing. As mentioned in our paper, SeQUeNCe is able to simulate portions of a network as different processes, where shared quantum states are tracked by a Quantum Manager Server running as a separate program.
For details on how to set up and run parallel simulations with SeQUeNCe, please follow the README instructions in the `../docs` directory to build the html documentation pages.
Parallel simulation information is listed under the "Parallel Simulation Pages" heading, and the source files may be found in `../docs/source/parallel`.

## Installing
Installation of SeQUeNCe includes the necessary simulation tools to run parallel simulations.
On top of this, an installation of an MPI implementation is required.
Additionally, if the C++ version of the Quantum Manager Server is used (see the Quantum Manager Server section), an installation of CMake and the Eigen library is required.
These instructions may also be viewed in the documentation on the "Prerequisites & Installation" page, and the source files are available at `../docs/source/parallel/install/prerequisite.md`.

### MPI
Most working MPI implementations can be used, preferably those supporting MPI-3 and built with shared/dynamic libraries. For a few options listed by the MPI for python package, please see [this documentation page](https://mpi4py.readthedocs.io/en/stable/appendix.html#building-mpi).

Once you have an MPI implementation installed, the MPI for python package should be added using the `../requirements.txt` file, or directly using pip as
```
$ pip install mpi4py
```
After this installation, parallel programs using the Python (not C++) version of the Quantum Manager Server (see the Quantum Manager Server section) are ready to run.

### CMake
To compile the C++ Server, CMake is required.
Instructions on how to install CMake can be found on the [CMake website](https://cmake.org/install/).
If you have CMake already installed on your system, make sure it is version 3.10 or later using `$ cmake --version`.

### Eigen
Eigen is also required for the C++ Server.
Eigen is a library for adding linear algebra tools to C++.
The library may be downloaded from the [Eigen wiki](http://eigen.tuxfamily.org/index.php?title=Main_Page#Download).
Once downloaded, create another directory named `build_dir` and build the library using cmake as:
```
$ mkdir build_dir
$ cd build_dir
$ cmake source_dir
$ make install
```
Where `source_dir` is the path to the downloaded Eigen files. The `make install` step may require administrator privileges.
For future reference and troubleshooting, these instructions may be viewed in the `INSTALL` file included with the Eigen library download.

## Quantum Manager Server
Before running a parallel simulation script, a quantum manager server must be started to service requests from the simulation clients. SeQUeNCe includes a server program written in Python for ease of use and customization, as well as a version written in C++ for improved performance. Both programs communicate with the simulation clients using sockets.
A description of how to run the server can be found in the documentation pages.

### C++ Server Build
NOTE: the C++ Quantum Manager Server requires C++17 or later to compile.

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

## Running a Parallel Script
Instructions of how to run a script in parallel with SeQUeNCe may be found in the documentation on the "Guide: Running a Parallel Script" page, with source code located at `../docs/source/parallel/guide/running_script.md`.
In general, this requires three steps:
- Modifying the usual simulation script to use available parallel processing. This includes modifying the JSON file to place objects on different processes, and adding a command to shut down a remote Quantum Manager Server.
- Running the Quantum Manager Server script, to begin listening for parallel processes. For the C++ version, this also includes compiling the server executable from the source files.
- Running the simulation script separately from the Quantum Manager Server, and observing results.

## Usage Examples
Some examples of how to set up and run parallel simulations are found in the `example` directory.
These showcase how a network may be allocated for parallel simulation with a few simple topologies, such as a linear and ring network.
