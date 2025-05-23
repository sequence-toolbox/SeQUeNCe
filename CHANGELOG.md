# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.7.2] - 2025-4-28

### Added
- New shields.io badges at for monthly downloads and python versions

### Changed
- Updated requirements.txt
- Updated demo codes


## [0.7.1] - 2025-4-25

### Added
New Component Modules from this paper: https://arxiv.org/pdf/2411.11031. 
- `qlan.graph_gen`
- `qlan.correction`
- `qlan.measurement`
- `topology.qlan.client`
- `topology.qlan.orchestrator`
- The unit tests in the folder `tests/qlan`
- Examples in the folder `example/qlan`.

New classes for classical nodes (no quantum attributes)
- `kernel.entity.ClassicalEntity`
- `topology.node.ClassicalNode`

### Changed
- Updated the code and examples related to the quantum transducer introduced in version 0.7.0
- Minor bug fixes and cosmetic updates
- Add new publications to README.md


## [0.7.0] - 2025-1-22

### Added
New Component Modules from this paper: https://arxiv.org/pdf/2411.11377. 
- `Transducer`
- `Transmon`
- `FockDetector`
- `FockBeamSplitter2`
- The unit tests in the folder `tests`
- Examples in the folder `example/quantum_transduction`.

### Changed
- Reorganized the `absorptive_memory` related files
- Update the `requirements.txt`
- Update `constants` module
- Update comments here and there


## [0.6.6] - 2024-12-17

### Added
- Add support for Python 3.13
- Add support for the latest Numpy (2.2), SciPy (1.14), and QuTiP (5.0)

### Changed
- Updated the demos of the tutorial for easy of understanding.
- Updated some comments, typing, arguments, and some other minor changes.
- Changelog updates: 
  - Reversed the changelog, now the latest version update is at the top of the changelog, instead of previously at the bottom. 
  - Added the timestamp for the version updates.

### Removed
- Removed support for Python 3.9


## [0.6.5] - 2024-11-20

### Added
- Add new class BellDiagonalState for Bell Diagonal State.
- Add new Quantum Manager for Bell Diagonal State, i.e., QuantumManagerBellDiagonal.
- Add new class SingleHeralded BSM to support single heralded entanglement generation.
- Add support for time-dependent decoherence for the Bell Diagonal State in Memory class.

### Changed
- Remove existing handlers in logging before setting the new handler


## [0.6.4] - 2024-9-26

### Changed
- Use `Read the Docs` for documentation. Update documentation. Old documentation website becomes obsolete. 
- Update comments and README.md

### Fixed
- Fix a bug in reservation protocol and routing protocol that may lead to route for src->dst being different than dst->src when the network has same length edges.


## [0.6.3] - 2024-8-12

### Added
- We have an Icon for SeQUeNCe!
- `pip install sequence` is now available!
- `src` folder is renamed to `sequence`
- Add `sequence/constants.py` to organize the common constants
- Add support for Python 3.12
- Add `pyproject.toml`

### Changed
- Various refactoring, include but not limited to updating variable/method names, moving/deleting code, adding/rewriting comments, and making the code more succinct, etc.
- In README.md, installation with option `--editable`  is encouraged.
- `logging` looks better
- In `class Reservation`, added attribute `entanglement_number` and `id`
- Update `ResourceReservationProtocol.load_rules()`
- Move `utils/json_config_generators/generator_utils.py` to `sequence/utils/config_generator.py`

### Removed
- Removed support for Python 3.8
- Removed `setup.py`
- Removed `MANIFEST.in`


## [0.6.2]

### Added
- Moved around and added a few files in the `examples` folder
  - These are primarily for the IEEE QCE 2023 conference

### Changed
- Modified the topology output of the GUI to be compatible with new topology upgrades
- Several bug fixes in the GUI


## [0.6.1]

### Added
- Added some groundwork for future topology upgrades

### Changed
- made numerous bug fixes:
  - BSM and optical channel components received fixes
  - Some residual bugs with GUI usage have been fixed
  - Error with typing in Fock quantum manager has been fixed

### Removed
- Removed support for scipy version 1.11. This is currently causing some issues with qutip.


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


## [0.5.4]

### Added
- Added some additional error checking to individual quantum states
  - This includes additional error checking in the `Photon` class

### Changed
- The `entangle` method for the `Photon` and `FreeQuantumState` classes has been changed to `combine_state`
- Updated chapter 1 tutorial in the documentation to match code example

### Removed
- residual `json5` references in examples


## [0.5.3]

### Changed
- Bug fixes to the GUI and QKD tests


## [0.5.2]

### Added
- Added more scripts for the QCE 2022 conference

### Changed
- Fixed some bugs in the GUI code for classical communication delay

### Removed
- Removed `mpi4py` from install instructions on the README


## [0.5.1]
### Changed
- Moved all parallel execution code to the parallel directory
  - Now installed as separate package `psequence`
  - New setup.py file and makefile specified in parallel folder
  - Minimum sequence requirement 0.5.1
- Parallel scripts are temporarily broken, will need to be rewritten for new structure

### Removed
- Removed `mpi4py` and `pytest-mpi` requirements for main package



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


## [0.3.2]

### Changed
- Corrected units in jupyter notebook example files
- Corrected units for the optical channel class
- Bug fixes for tutorial scripts


## [0.3.1]

### Added
- `Mirror` class for simple reflection of photons
  - Sends photon to another node with quantum channel connection to the local node
- Quantum++ package acknowledgement to README


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


## [0.2.3]

### Added
- quantum state manager for quantum memories
- quantum circuit class (for use with quantum memories)
- `qutip` library dependency

### Changed
- rewrite of quantum entanglement class
- change all optical channels to one-way


## [0.2.2]

### Added
- logging functionality with `log` module
- cached quantum state measurement

### Changed
- changed all quantum state representations from list to tuple
- event removal system
- example scripts now use `Timeline.seed()` method
- `Timeline` event removal method


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

