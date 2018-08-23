import os
import re

from setuptools import setup, find_packages


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, 'multiscanner', 'version.py')

REQ_REGEX = re.compile(r'^(?!#)(?!git+)(?!-r).*$')
DEPS_LINKS_REGEX = re.compile(r'(^git+.*$)')


def get_version():
    with open(VERSION_FILE) as f:
        for line in f.readlines():
            if line.startswith('__version__'):
                version = line.split()[-1].strip('\'')
                return version
        raise AttributeError('Package does not have a __version__')


def get_requirements(filename, dep_links_only=False):
    requirements = []
    with open(filename) as f:
        for l in f.readlines():
            if dep_links_only is False and REQ_REGEX.match(l):
                requirements.append(l.strip())
            elif dep_links_only is True and DEPS_LINKS_REGEX.match(l):
                requirements.append(l.strip())
    if requirements:
        return requirements
    msg = 'Unable to extract requirements from {}'.format(filename)
    raise RuntimeError(msg)


def get_long_description():
    with open('README.md') as f:
        return f.read()


setup(
    name='multiscanner',
    version=get_version(),
    url='https://github.com/mitre/multiscanner',
    license='MPL 2.0',
    author='Drew Bonasera',
    packages=find_packages(exclude=['*.tests']),
    include_package_data=True,
    description='A file analysis framework that allows the user to evaluate a set of files with a set of tools.',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    keywords='malware research analysis scanning framework modular',
    install_requires=get_requirements('requirements.txt'),
    entry_points={
        'console_scripts': [
            'multiscanner=multiscanner.ms:_main',
            'multiscanner-web=multiscanner.web.app:_main',
            'multiscanner-api=multiscanner.distributed.api:_main',
        ],
    },
    extras_require={
        'dev': get_requirements('requirements-test.txt') + get_requirements('requirements-dev.txt'),
        'test': get_requirements('requirements-test.txt'),
    },
    dependency_links=get_requirements('requirements.txt', dep_links_only=True),
    classifiers=[
        'Framework :: MultiScanner',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
    ],
)
