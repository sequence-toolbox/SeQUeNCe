<p align="center">
  <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/docs/Sequence_Icon_Name_Dark.png">
   <img src="https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/docs/Sequence_Icon_Name.svg" alt="sequence icon" width="450" class="center">
  </picture>
</p>

<h3><p align="center">Quantum Networking in SeQUeNCe: Customizable, Scalable, Easy Debugging</p></h3>


[![Documentation](https://img.shields.io/readthedocs/sequence-rtd-tutorial)](https://sequence-rtd-tutorial.readthedocs.io/)
[![PyPi](https://img.shields.io/pypi/v/sequence)](https://pypi.org/project/sequence/)
[![Qutip](https://img.shields.io/badge/integration%20-Qutip-blue)](https://qutip.org/)
[![Paper](https://img.shields.io/badge/10.1088%2F2058-9565%2Fac22f6?label=DOI)](https://iopscience.iop.org/article/10.1088/2058-9565/ac22f6)



<br>

## SeQUeNCe: Simulator of QUantum Network Communication

SeQUeNCe is an open source, discrete-event simulator for quantum networks. As described in our [paper](http://arxiv.org/abs/2009.12000), the simulator includes 5 modules on top of a simulation kernel:
* Hardware
* Entanglement Management
* Resource Management
* Network Management
* Application

These modules can be edited by users to define additional functionality and test protocol schemes, or may be used as-is to test network parameters and topologies.

## Installing
SeQUeNCe requires [Python](https://www.python.org/downloads/) 3.9 or later. You can simply install SeQUeNCe using `pip`:
```
pip install sequence
```

If you wish to make your own edits to the codebase, SeQUeNCe should be installed in [development mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html) (a.k.a. editable install).
To do so, clone and install the simulator as follows:
```
git clone https://github.com/sequence-toolbox/SeQUeNCe.git
cd SeQUeNCe
make install_editable
```

If you do not have `make` command (i.e., Windows user), replace `make install_editable` with `pip install --editable . --config-settings editable_mode=strict`.


## Citation
Please cite us, thank you!
```
@article{sequence,
author = {Xiaoliang Wu and Alexander Kolar and Joaquin Chung and Dong Jin and Tian Zhong and Rajkumar Kettimuthu and Martin Suchara},
title = {SeQUeNCe: a customizable discrete-event simulator of quantum networks},
journal = {Quantum Science and Technology},
volume = {6},
year = {2021},
month = {sep},
doi = {10.1088/2058-9565/ac22f6},
url = {https://dx.doi.org/10.1088/2058-9565/ac22f6},
publisher = {IOP Publishing},
}
```

<!-- * X. Wu, A. Kolar, J. Chung, D. Jin, T. Zhong, R. Kettimuthu and M. Suchara. "SeQUeNCe: Simulator of QUantum Network Communication." GitHub repository, https://github.com/sequence-toolbox/SeQUeNCe, 2021. -->

## Running the GUI
Once SeQUeNCe has been installed as described above, simply run the `gui.py` script found in the root of the project directory
```
python gui.py
```

## Usage Examples
Many examples of SeQUeNCe in action can be found in the [example](/example) folder. These include both quantum key distribution and entanglement distribution examples.

### Starlight Experiments
Code for the experiments performed in our paper can be found in the file `starlight_experiments.py`. This script uses the `starlight.json` file (also within the example folder) to specify the network topology.

### Jupyter Notebook Examples
The example folder contains several scripts that can be run with jupyter notebook for easy editing and visualization. These files require that the notebook package be installed (Anaconda recommended):
```
pip install notebook
pip install ipywidgets
```
To run each file, simply run
```
jupyter notebook <filename>
```
These examples include:
* `BB84_eg.ipynb`, which uses the BB84 protocol to distribute secure keys between two quantum nodes
* `two_node_eg.ipynb`, which performs entanglement generation between two adjacent quantum routers
* `three_node_eg_ep_es.ipynb`, which performs entanglement generation, purification, and swapping for a linear network of three quantum routers

## Additional Tools

### Network Visualization
The example directory contains an example json file `starlight.json` to specify a network topology, and the utils directory contains the script `draw_topo.py` to visualize json files. To use this script, the Graphviz library must be installed. Installation information can be found on the [Graphviz website](https://www.graphviz.org/download/).

To view a network, simply run the script and specify the relative location of your json file:
```
python utils/draw_topo.py example/starlight.json
```
This script also supports a flag `-m` to visualize BSM nodes created by default on quantum links between routers.

## Libraries Used
This project includes a modified fork of the Quantum++ library version 2.6.
Please see the Quantum++ [`LICENSE`](https://github.com/softwareQinc/qpp/blob/main/LICENSE) file for more information.

## Contact
If you have questions, please contact [Caitao Zhan](https://caitaozhan.github.io/) at [czhan@anl.gov](mailto:czhan@anl.gov).

## Papers that Used and/or Extended SeQUeNCe

* X. Wu et al., ["Simulations of Photonic Quantum Networks for Performance Analysis and Experiment Design"](https://ieeexplore.ieee.org/document/8950718), IEEE/ACM Workshop on Photonics-Optics Technology Oriented Networking, Information and Computing Systems (PHOTONICS), 2019

* X. Wu, A. Kolar, J. Chung, D. Jin, T. Zhong, R. Kettimuthu and M. Suchara. ["SeQUeNCe: A Customizable Discrete-Event Simulator of Quantum Networks"](https://iopscience.iop.org/article/10.1088/2058-9565/ac22f6), Quantum Science and Technology, 2021

* V. Semenenko et al., ["Entanglement generation in a quantum network with finite quantum memory lifetime"](https://pubs.aip.org/avs/aqs/article/4/1/012002/2835237/Entanglement-generation-in-a-quantum-network-with), AVS Quantum Science, 2022

* A. Zang et al., ["Simulation of Entanglement Generation between Absorptive Quantum Memories"](https://ieeexplore.ieee.org/abstract/document/9951205), IEEE QCE 2022

* M.G. Davis et al., ["Towards Distributed Quantum Computing by Qubit and Gate Graph Partitioning Techniques"](https://ieeexplore.ieee.org/abstract/document/10313645), IEEE QCE 2023

* R. Zhou et al., ["A Simulator of Atom-Atom Entanglement with Atomic Ensembles and Quantum Optics"](https://ieeexplore.ieee.org/abstract/document/10313610), IEEE QCE 2023

* X. Wu et al., ["Parallel Simulation of Quantum Networks with Distributed Quantum State Management"](https://dl.acm.org/doi/abs/10.1145/3634701), ACM Transactions on Modeling and Computer Simulation, 2024

* C. Howe, M. Aziz, and A. Anwar, ["Towards Scalable Quantum Repeater Networks"](https://arxiv.org/abs/2409.08416), arXiv preprint, 2024

* A. Zang et al., ["Quantum Advantage in Distributed Sensing with Noisy Quantum Networks"](https://arxiv.org/abs/2409.17089), arXiv preprint, 2024


Please do a Pull Request to add your paper here! 
