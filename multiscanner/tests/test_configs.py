from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import mock
import os
import tempfile

import multiscanner
from multiscanner.common import utils

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))

mock_modlist = {'test_conf': [True, os.path.join(CWD, 'modules')]}
filelist = utils.parse_dir(os.path.join(CWD, 'files'))
module_list = ['test_conf']


@mock.patch('multiscanner.ms.MODULE_LIST', mock_modlist)
def test_no_config():
    results, metadata = multiscanner.multiscan(
        filelist, config=None,
        recursive=None, module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'b', 'c': 'd'}


@mock.patch('multiscanner.ms.MODULE_LIST', mock_modlist)
def test_config_api_no_file():
    config = {'test_conf': {'a': 'z'}}
    results, metadata = multiscanner.multiscan(
        filelist, config=config,
        recursive=None, module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}


@mock.patch('multiscanner.ms.MODULE_LIST', mock_modlist)
def test_config_api_with_empty_file():
    config = {'test_conf': {'a': 'z'}}
    config_file = tempfile.mkstemp()[1]
    multiscanner.update_ms_config_file(config_file)
    results, metadata = multiscanner.multiscan(
        filelist, config=config,
        recursive=None, module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}


@mock.patch('multiscanner.ms.MODULE_LIST', mock_modlist)
def test_config_api_with_real_file():
    config = {'test_conf': {'a': 'z'}}
    config_file = tempfile.mkstemp()[1]
    multiscanner.config_init(config_file)
    multiscanner.update_ms_config_file(config_file)
    results, metadata = multiscanner.multiscan(
        filelist, config=config,
        recursive=None, module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}
