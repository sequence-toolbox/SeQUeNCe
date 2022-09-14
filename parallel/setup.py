from setuptools import setup

setup(
    name="psequence",
    version="0.1.0",
    author="Xiaoliang Wu, Joaquin Chung, Alexander Kolar, Alexander Kiefer, Eugene Wang, Tian Zhong,"
           " Rajkumar Kettimuthu, Martin Suchara",
    author_email="xwu64@hawk.iit.edu, chungmiranda@anl.gov, akolar@anl.gov, akiefer@iu.edu, eugenewang@yahoo.com,"
                 " tzh@uchicago.edu, kettimut@mcs.anl.gov, msuchara@anl.gov",
    description="Parallel extension for SEQUENCE."
                " SEQUENCE-Python is a prototype version of the official SEQUENCE release.",
    packages=['psequence', 'psequence.p_quantum_manager', 'psequence.p_router_net_topo',
              'psequence.p_timeline', 'psequence.p_timeline',
              'psequence.quantum_manager_client', 'psequence.quantum_manager_server'],
    package_dir={'sequence': 'src'},
    package_data={'sequence': ['gui/user_templates.json', 'gui/default_params.json', 'gui/starlight.json']},
    include_package_data=True,
    install_requires=[
        'numpy>=1.22',
        'pandas',
        'qutip>=4.6.0',
        'tqdm>=4.54.0',
        'mpi4py',
        'pytest-mpi',
        'sequence>=0.5.0'
    ],
)
