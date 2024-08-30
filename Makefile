all: jupyter

setup:
	pip3 install -r ./requirements.txt

install:
	pip3 install .

install_editable:
	pip3 install --editable . --config-settings editable_mode=strict

jupyter:
	jupyter notebook ./example/two_node_eg.ipynb

test:
	pip3 install .
	pytest ./tests