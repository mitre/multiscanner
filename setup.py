from __future__ import print_function
import sys
from distutils.core import setup

if ['-c', 'egg_info'] != sys.argv and ['-c', 'develop', '--no-deps'] != sys.argv[:3]:
    print("ERROR: This only works in development mode", file=sys.stderr)
    exit(-1)

setup(
    name='multiscanner',
    version='0.9.1',
    url='https://github.com/MITRECND/multiscanner',
    license='MPL 2.0',
    author='Drew Bonasera',
    author_email='',
    description='A file analysis framework that allows the user to evaluate a set of files with a set of tools.',
)
