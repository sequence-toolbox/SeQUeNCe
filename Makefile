all: jupyter

setup:
	pip install -r ./requirements.txt

install:
	pip install .

install_editable:
	pip install --editable . --config-settings editable_mode=strict

jupyter:
	jupyter notebook ./example/two_node_eg.ipynb

test:
	pip install .
	pytest ./tests