all: jupyter

setup:
	pip3 install -r ./requirements.txt

install_no_pip:
	python3 setup.py install

install:
	pip3 install .

jupyter:
	jupyter notebook ./example/two_node_eg.ipynb

test:
	python3 setup.py install
	pytest ./tests
