# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1]
### Added
- observer functionality for entities
- README file for documentation

### Changed
- some method-level docstrings
- convert all component constructors from keyword to positional arguments
- change documentation directory from `sphinx` to `docs`

### Removed
- push/pop functions for entities and non-stack protocols
- some unnecessary entity attributes

## [0.2.2]
### Added
- logging functionality with `log` module
- cached quantum state measurement

### Changed
- changed all quantum state representations from list to tuple
- event removal system
- example scripts now use `Timeline.seed()` method
- `Timeline` event removal method

## [0.2.3]
### Added
- quantum state manager for quantum memories
- quantum circuit class (for use with quantum memories)
- `qutip` library dependency

### Changed
- rewrite of quantum entanglement class
- change all optical channels to one-way

## [0.2.4]
### Added
- serialization of messages, circuits
- base classes for applications and quantum manager states
- photon loss method `Photon.add_loss()`

### Changed
- moved all random number generation to network nodes
  - includes all components and quantum manager functions
  - utilizes `Entity.get_generator()` method
- reworked timeline events to handle cross-process events
  - most protocols and components now use strings instead of explicit instances for classes
- tweaked process of entangelement and reservation protocols
- `EventList` structure and interface with `Timeline`
- `Timeline` timing display

## [0.3.0]
### Added
- parallel execution for the kernel module
- `parallel` directory with useful tools
  - Python and C++ servers for managing parallel kernel executions
  - Many examples for parallel execution
- updated documentation with parallel code
- utility files for generating network config JSON files

### Changed
- `Topology` class has been made into a simplified base class
  - `RouterNetTopo` and `QKDTopo` classes added for specific network types
- tweaked library dependencies
  - added `mpi4py` and `mpi-pytest` requirements for parallel execution
  - removed `json5` requirement

## [0.3.1]
### Added
- `Mirror` class for simple reflection of photons
  - Sends photon to another node with quantum channel connection to the local node
- Quantum++ package acknowledgement to README

## [0.3.2]
### Changed
- Corrected units in jupyter notebook example files
- Corrected units for the optical channel class
- Bug fixes for tutorial scripts

## [0.4.0]
### Added
- GUI for ease of simulation setup
- Framework for future GUI usage to run simulations
  - This feature is currently unimplemented and will not work
- Package dependencies for GUI (dash and plotly)

### Changed
- Updated version requirement for numpy
  - This removes support for Python 3.7 and below
- Bug fixes to tutorial chapter 3
- Typo fixes to docstrings in reservation.py

## [0.5.0]
### Added
- Tutorial materials for IEEE Quantum Week 2022 tutorial session

### Changed
- Reworked interface for nodes and hardware elements
  - New Entity interface for receiving/passing photons
  - New method for nodes to handle incoming and outgoing qubits
  - Polished observer functionality
- Reworked some protocols to utilize new interface
- Some bug fixes for GUI

## [0.5.1]
### Changed
- Moved all parallel execution code to the parallel directory
  - Now installed as separate package `psequence`
  - New setup.py file and makefile specified in parallel folder
  - Minimum sequence requirement 0.5.1
- Parallel scripts are temporarily broken, will need to be rewritten for new structure

### Removed
- Removed `mpi4py` and `pytest-mpi` requirements for main package

## [0.5.2]
### Added
- Added more scripts for the QCE 2022 conference

### Changed
- Fixed some bugs in the GUI code for classical communication delay

### Removed
- Removed `mpi4py` from install instructions on the README

## [0.5.3]
### Changed
- Bug fixes to the GUI and QKD tests

## [0.5.4]
### Added
- Added some additional error checking to individual quantum states
  - This includes additional error checking in the `Photon` class

### Changed
- The `entangle` method for the `Photon` and `FreeQuantumState` classes has been changed to `combine_state`
- Updated chapter 1 tutorial in the documentation to match code example

### Removed
- residual `json5` references in examples

## [0.6.0]
### Added
- Fock state density matrix encoding
- Quantum manager to use fock state density matrix
  - Add truncation attribute to quantum managers; Hilbert space dimension is truncation + 1
  - Supports error channels based on kraus operators and direct operator action on state
- Hardware models to use fock state density matrix
  - Absorptive quantum memory built on AFC
  - Interference and direct detection for state tomography

### Changed
- Moved around and updated some error checking
- Temporarily removed mpich testing for python 3.8 and 3.9 (broken)
