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
- change documentation directory from "sphinx" to "docs"

### Removed
- push/pop functions for entities and non-stack protocols
- some unnecessary entity attributes

## [0.2.2]
### Added
- logging functionality with "log" module
- cached quantum state measurement

### Changed
- changed all quantum state representations from list to tuple
- event removal system
- example scripts now use "Timeline.seed()" method
- Timeline event removal method

## [0.2.3]
### Added
- quantum state manager for quantum memories
- quantum circuit class (for use with quantum memories)
- Qutip library dependency

### Changed
- rewrite of quantum entanglement class
- change all optical channels to one-way
