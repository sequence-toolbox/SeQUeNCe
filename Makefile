all: jupyter

jupyter:
	jupyter notebook ./example/two_node_eg.ipynb

test:
	python3 -m pytest ./tests
