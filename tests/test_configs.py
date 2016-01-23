from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import sys
import tempfile

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(CWD))
import multiscanner
sys.path.append(os.path.join(CWD, '..', 'libs'))
import common
multiscanner.MODULEDIR = os.path.join(CWD, "modules")

module_list = [os.path.join(CWD, 'modules', 'test_conf.py')]
filelist = common.parseDir(os.path.join(CWD, 'files'))

def test_no_config():
    results, metadata = multiscanner.multiscan(filelist, configfile=None, config=None, recursive=None, module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'b', 'c': 'd'}

def test_config_api_no_file():
    config = {'test_conf': {'a': 'z'}}
    results, metadata = multiscanner.multiscan(filelist, configfile=None, config=config, recursive=None, module_list=module_list)[0]
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}

def test_config_api_with_empty_file():
    config = {'test_conf': {'a': 'z'}}
    config_file = tempfile.mkstemp()[1]
    results, metadata = multiscanner.multiscan(filelist, configfile=config_file, config=config, recursive=None, module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}

def test_config_api_with_real_file():
    config = {'test_conf': {'a': 'z'}}
    config_file = tempfile.mkstemp()[1]
    multiscanner.config_init(config_file)
    results, metadata = multiscanner.multiscan(filelist, configfile=config_file, config=config, recursive=None, module_list=module_list)[0]
    os.remove(config_file)
    assert metadata['conf'] == {'a': 'z', 'c': 'd'}
