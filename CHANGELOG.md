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
