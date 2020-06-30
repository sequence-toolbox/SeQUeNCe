# SEQUENCE-Python

fff

SEQUENCE-Python is a prototype version of official SEQUENCE release. We will use SEQUENCE-Python to demonstrate our design. To avoid confusion, we create a seperate repository to mange code for SEQUENCE-Python. 

Example code for the final version of the model can be found in "sequence.py", which relies on the unfinished parser.
Running code for the BB84 protocol can be found in "BB84.py".

## Requirements

### Install json5 (json5)

```
$ pip3 install json5
```

### Install numba

```
$ pip3 install numba
```

### Install pandas

```
$ pip3 install pandas
```

### Jupyter Notebook

* Installation 

```shell script
$ pip3 install notebook
```

* Run

```shell script
$ jupyter notebook
```

Add Virtual Environment to Jupyter Notebook (Optional)

* Activate the virtualenv

```shell script
$ source your-venv/bin/activate
```

* Install jupyter in the virtualenv

```shell script
(your-venv)$ pip install jupyter
```

* Add the virtualenv as a jupyter kernel

```shell script
(your-venv)$ ipython kernel install --name "local-venv" --user

```

You can now select the created kernel your-env when you start Jupyter

## Useful info

### Profiling with py-spy
First, ensure that py-spy is installed:
```shell script
$ pip3 install py-spy
```
To display the output of a program as a flame graph, use the `record` command on either a currently running process or a python program:
```shell script
$ py-spy record -o profile.svg --pid 1234
$ py-spy record -o profile.svg -- python3 program.py
```
The `top` command can also be used to show real-time usage. More details can be found on the project page [here](http://pypi.org/project/py-spy/).

### Generating class diagram with pylint

First, ensure that pylint is installed:
```shell script
$ pip3 install pylint
```
To output a png image, the Graphviz package must be installed. This can be downloaded from the graphviz website [here](graphviz.org). Finally, run the command
```shell script
$ pyreverse src -o png
```
to generate the class diagram as a .png image.
