all: jupyter

setup:
	pip3 install -r ./requirements.txt

install:
	pip3 install .

jupyter:
	jupyter notebook ./example/two_node_eg.ipynb

test:
	pip3 install .
	pytest ./tests