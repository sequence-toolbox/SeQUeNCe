all: jupyter

jupyter:
	jupyter notebook ./example/two_node_eg.ipybn

test:
	python3 -m pytest ./tests
