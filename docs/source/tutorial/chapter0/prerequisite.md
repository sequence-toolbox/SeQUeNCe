# Prerequisites & Installation

Thank you for downloading SeQUeNCe and welcome to the tutorial section of the documentation. The following 6 chapters will give an overview of the modules available in the simulator and how they can be used to build network simulations. In this first chapter we will review how to set up a working environment for SeQUeNCe.

## Prerequisites

### Python Version

The simulator requires at least version 3.7 of Python. This can be found at the [Python Website](https://www.python.org/downloads/).

### Dependencies

The simulator requires the following Python libraries:
* `numpy`, for mathematical computing tasks
* `json5` version 0.8.4, for interpretation of json configuration files
* `pandas`, for data processing
* `matplotlib`, for generating graphics
* `qutip` version 4.6.0 or later, for quantum circuit management

These will be installed automatically with the simulator if they are not already present. Also note that the `sequence` library found on PyPI cannot be installed, as it will conflict with the simulator library.

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

### Install SeQUeNCe

We can now download and install the simulator. The code can be cloned easily using `git`, and installed with the native python installer `pip`:

```shell script
$ git clone https://github.com/sequence-toolbox/SeQUeNCe.git
$ cd Sequence-python
$ pip install .
```

`pip install` will use the `requirements.txt` file to install necessary dependencies and the `setup.py` file to build the `sequence` library. The simulator is now ready to use.
