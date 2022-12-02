install_no_pip:
	python3 setup.py install

install:
	pip3 install .

test_parallel:
	mpiexec -n 2 pytest ./tests_parallel --with-mpi