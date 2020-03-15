# SEQUENCE-Python

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