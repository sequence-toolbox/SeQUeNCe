# Prerequisites & Installation

This set of three pages will go through the setup and usage of SeQUeNCe's parallel simulation capabilities. In this first page, we will review how to install the necessary requirements for parallel simulation.

## Additional Required Installations
To run the parallel simulations fully in Python, the MPI for Python library must be installed.
The rest of the parallel simulation will then work with installation of the parallel SeQUeNCe library `psequence`.

### MPI for Python
Before installing MPI for Python, an implementation of MPI must be installed on your system. Most working MPI implementations can be used, preferably those supporting MPI-3 and built with shared/dynamic libraries. For a few options listed by the MPI for python package, please see [this documentation page](https://mpi4py.readthedocs.io/en/stable/appendix.html#building-mpi).

After this has been completed, the Python library may be installed as
```
$ pip install mpi4py
```

### Parallel SeQUeNCe
After this, the parallel `psequence` package may be installed.
This is handled in a similar manner to the base package; simply navigate to the parallel folder and run
```
$ pip install .
```
Or, using the included makefile,
```
$ make install
```

## C++ Quantum Manager Server
In addition to the Quantum Manager Server written in Python, SeQUeNCe also provides a version of the server written in C++. This version also provides multithreading to support the processing of multiple Quantum Manager Client requests, and generally results in performance increases (see our paper TODO: add link). To run this version, a few additional steps must be taken:
* Installing CMake, a tool for managing and compiling the Quantum Manager Server code,
* Installing Eigen, a linear algebra library for C++, and
* Building the executable from the C++ source files.

Please also note that your C++ compiler should be using version C++17 or later. Checking and updating the compiler version is not covered on this page.

### Installing CMake
SeQUeNCe uses CMake to efficiently manage the quantum server build and library dependencies. Instructions on how to install CMake can be found on the [CMake website](https://cmake.org/install/). If you have CMake already installed on your system, make sure it is version 3.10 or later using the command
```
$ cmake --version
```

### Installing Eigen
Eigen may be downloaded from the [Eigen wiki](http://eigen.tuxfamily.org/index.php?title=Main_Page#Download). Once downladed, the library should be built using CMake. To do this, create another directory named `build_dir` and build the library as such:
```
$ mkdir build_dir
$ cd build_dir
$ cmake source_dir
$ make install
```
Where `source_dir` is the path to the downloaded Eigen files. The `make install` step may require administrator privileges. For future reference, these instructions may be viewed in the `INSTALL` file included with the Eigen library download.

### Building the Quantum Manager Server
After installing CMake and Eigen, we can build and run the Quantum Manager Server. First, navigate to the cpp\_server directory and create a build directory:
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
