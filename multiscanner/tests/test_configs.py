from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import mock
import os
import tempfile

import multiscanner
from multiscanner.common import utils

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))

mock_modlist = {'test_conf': [True, os.path.join(CWD, 'modules')]}
mock_modlist2 = {'test_conf': [True, os.path.join(CWD, 'modules')],
                 'test_1': [True, os.path.join(CWD, 'modules')],
                 'test_2': [True, os.path.join(CWD, 'modules')]}
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


@mock.patch('multiscanner.config.MODULE_LIST', mock_modlist2)
def test_config_reset_not_overwrite():
    config_file = tempfile.mkstemp()[1]
    module_list = multiscanner._get_main_modules()
    multiscanner.config_init(config_file, module_list)
    multiscanner.update_ms_config_file(config_file)

    # Change a config val from default
    config_object = multiscanner.MSConfigParser()
    config_object.read(config_file)
    config_object.set('test_2', 'ENABLED', 'False')
    with open(config_file, 'w') as conf_file:
        config_object.write(conf_file)

    # call config_init with overwrite=true, but since test_2 isn't in the module list it won't be overwritten
    del module_list['test_2']
    multiscanner.config.config_init(config_file, module_list, True)
    multiscanner.update_ms_config_file(config_file)
    os.remove(config_file)
    assert multiscanner.config.MS_CONFIG.get('test_2', 'ENABLED') is False
