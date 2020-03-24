all: jupyter

setup:
	pip3 install -r ./requirements.txt
	python3 setup.py install

jupyter:
	jupyter notebook ./example/two_node_eg.ipynb

test:
	python3 -m pytest ./tests
