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


def test_config_parse_round_trip():
    conf_dict = {'test': {'a': 'b', 'c': 'd'}}
    conf_parser = multiscanner.config.dict_to_config(conf_dict)
    assert conf_parser.get('test', 'a') == 'b'
    conf_dict2 = multiscanner.config.parse_config(conf_parser)
    assert conf_dict == conf_dict2


@mock.patch('multiscanner.config.MODULE_LIST', mock_modlist)
def test_no_config():
    results, metadata = multiscanner.multiscan(
        filelist, config=None,
        module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'b', 'c': 'd'}


@mock.patch('multiscanner.config.MODULE_LIST', mock_modlist)
def test_config_api_no_file():
    config = multiscanner.config.dict_to_config({'test_conf': {'a': 'z'}})
    results, metadata = multiscanner.multiscan(
        filelist, config=config,
        module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}


@mock.patch('multiscanner.config.MODULE_LIST', mock_modlist)
def test_config_api_with_empty_file():
    config = multiscanner.config.dict_to_config({'test_conf': {'a': 'z'}})
    config_file = tempfile.mkstemp()[1]
    multiscanner.update_ms_config_file(config_file)
    results, metadata = multiscanner.multiscan(
        filelist, config=config,
        module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}


@mock.patch('multiscanner.config.MODULE_LIST', mock_modlist)
def test_config_api_with_real_file():
    config = multiscanner.config.dict_to_config({'test_conf': {'a': 'z'}})
    config_file = tempfile.mkstemp()[1]
    module_list = multiscanner._get_main_modules()
    multiscanner.config_init(config_file, module_list)
    multiscanner.update_ms_config_file(config_file)
    results, metadata = multiscanner.multiscan(
        filelist, config=config,
        module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}
