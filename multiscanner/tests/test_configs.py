from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import tempfile

import multiscanner
from multiscanner.common import utils

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))

module_list = [os.path.join(CWD, 'modules', 'test_conf.py')]
filelist = utils.parseDir(os.path.join(CWD, 'files'))


def test_no_config():
    results, metadata = multiscanner.multiscan(
        filelist, configfile=None, config=None,
        recursive=None, module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'b', 'c': 'd'}


def test_config_api_no_file():
    config = {'test_conf': {'a': 'z'}}
    results, metadata = multiscanner.multiscan(
        filelist, configfile=None, config=config,
        recursive=None, module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}


def test_config_api_with_empty_file():
    config = {'test_conf': {'a': 'z'}}
    config_file = tempfile.mkstemp()[1]
    results, metadata = multiscanner.multiscan(
        filelist, configfile=config_file, config=config,
        recursive=None, module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}


def test_config_api_with_real_file():
    config = {'test_conf': {'a': 'z'}}
    config_file = tempfile.mkstemp()[1]
    multiscanner.config_init(config_file)
    results, metadata = multiscanner.multiscan(
        filelist, configfile=config_file, config=config,
        recursive=None, module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}
