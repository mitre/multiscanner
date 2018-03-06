from __future__ import print_function
import os
from distutils.core import setup


def recursive_dir_list(path, exclude=['.pyc', '__pycache__']):
    ret = []
    for item in os.listdir(path):
        fail = False
        for test in exclude:
            if item.endswith(test):
                fail = True
                continue
        if fail:
            continue

        item = os.path.join(path, item)
        if os.path.isdir(item):
            ret.extend(recursive_dir_list(item))
        else:
            ret.append(item)
    return ret

to_walk = ['docs', 'etc', 'libs', 'modules', 'storage', 'utils']
data_files = []
for directory in to_walk:
    data_files.extend(recursive_dir_list(directory))

setup(
    name='multiscanner',
    version='0.9.2',
    url='https://github.com/MITRECND/multiscanner',
    license='MPL 2.0',
    author='Drew Bonasera',
    author_email='',
    packages=['multiscanner'],
    package_dir={'multiscanner': '.'},
    package_data={'multiscanner': data_files},
    description='A file analysis framework that allows the user to evaluate a set of files with a set of tools.',
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
        'console_scripts': ['multiscanner=multiscanner:_main']
    }
)
