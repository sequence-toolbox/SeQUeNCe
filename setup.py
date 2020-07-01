from setuptools import setup

setup(
    name="sequence",
    version="0.1",
    author="Xiaoliang Wu, Joaquin Chung, Alexander Kolar, Eugene Wang, Tian Zhong, Rajkumar Kettimuthu, Martin Suchara",
    author_email="xwu64@hawk.iit.edu, chungmiranda@anl.gov, akolar@anl.gov, eugenewang@yahoo.com, tzh@uchicago.edu, kettimut@mcs.anl.gov, msuchara@anl.gov",
    description="Simulator of Quantum Network Communication: SEQUENCE-Python is a prototype version of official SEQUENCE release. ",
    # packages = find_packages('src'),
    packages=['sequence', 'sequence.app', 'sequence.kernel', 'sequence.components', 'sequence.protocols',
              'sequence.protocols.network_management',
              'sequence.protocols.entanglement_management', 'sequence.protocols.qkd', 'sequence.protocols.resource_management',
              'sequence.topology', 'sequence.utils'],
    package_dir={'sequence': 'src'},
    install_requires=[
        'setuptools',
        'json5',
        'numba',
        'pandas'
    ],
)
