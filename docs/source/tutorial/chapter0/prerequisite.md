# Prerequisites & Installation

Thank you for downloading SeQUeNCe and welcome to the tutorial section of the documentation. The following 6 chapters will give an overview of the modules available in the simulator and how they can be used to build network simulations. In this first chapter we will review how to set up a working environment for SeQUeNCe.

## Prerequisites

### Python Version

The simulator requires at least version **3.10** of Python. This can be found at the [Python Website](https://www.python.org/downloads/).

### Dependencies

The simulator requires the following Python libraries:
* `qutip`,for quantum circuit management
* `networkx`, for network topology related operations
* `numpy`, for mathematical computing tasks
* `scipy`, for linear algebra computing tasks
* `pandas`, for data processing
* `matplotlib`, for generating graphics

These will be installed automatically with the simulator if they are not already present. 

## Installation

### Create virtual environment

It is often useful to create a clean working directory from which to run the simulator. This can be easily achieved with the Python `venv` module. A new virtual environment can be created as

```shell script
$ python3 -m venv path-to-venv
```

which will create a new virtual environment at the specified path. It can then be activated with

```shell script
$ source path-to-venv/bin/activate
```

The shell prompt should now show the name of the virtual environment.

Using Anaconda/conda to create a virtual environment is also recommended.

### Install SeQUeNCe

You can simply install SeQUeNCe using `pip`:
```
pip install sequence
```

If you wish to make your own edits to the codebase, SeQUeNCe should be installed in [development mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html) (a.k.a. editable install).
To do so, clone and install the simulator as follows:
```
git clone https://github.com/sequence-toolbox/SeQUeNCe.git
cd SeQUeNCe
pip install --editable . --config-settings editable_mode=strict
```

