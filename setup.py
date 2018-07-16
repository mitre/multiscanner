from __future__ import print_function
import os
from setuptools import setup, find_packages


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, 'multiscanner', 'version.py')


def get_version():
    with open(VERSION_FILE) as f:
        for line in f.readlines():
            if line.startswith('__version__'):
                version = line.split()[-1].strip('\'')
                return version
        raise AttributeError('Package does not have a __version__')


with open('README.md') as f:
    long_description = f.read()

setup(
    name='multiscanner',
    version=get_version(),
    url='https://github.com/mitre/multiscanner',
    license='MPL 2.0',
    author='Drew Bonasera',
    packages=find_packages(exclude=['*.tests']),
    include_package_data=True,
    description='A file analysis framework that allows the user to evaluate a set of files with a set of tools.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='malware research analysis scanning framework modular',
    install_requires=[
        'future',
        'configparser',
        # Required by modules
        'bitstring',
        'paramiko',
        'pefile',
        'pyclamd',
        'python-magic',
        'requests',
        'ssdeep',
        # Required for STIX2 content
        'six',
        'stix2',
        # Required by PDF
        'reportlab',
        # Required by API
        'flask',
        'sqlalchemy',
        'sqlalchemy-utils',
        # Required by storage modules
        'elasticsearch',
        'pymongo',
    ],
    entry_points={
        'console_scripts': ['multiscanner=multiscanner.multiscanner:_main'],
    },
    extras_require={
        'dev': ['flake8', 'pre-commit'],
        'test': ['Flask-Testing', 'mock', 'pathlib', 'pytest', 'selenium'],
    },
    classifiers=[
        'Framework :: MultiScanner',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
    ],
)
