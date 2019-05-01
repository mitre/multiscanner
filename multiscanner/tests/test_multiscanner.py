from __future__ import division, absolute_import, print_function, unicode_literals
import os
import sys

import multiscanner
from multiscanner.common import utils

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))

TEST_CONFIG_FILE = '.tmpfile.ini'
TEST_REPORT = 'tmp_report.json'


class _runmulti_tests(object):
    @classmethod
    def setup_class(cls):
        cls.real_mod_dir = multiscanner.config.MODULES_DIR
        cls.real_mod_list = multiscanner.config.MODULE_LIST
        multiscanner.config.MODULES_DIR = os.path.join(CWD, "modules")
        multiscanner.config.MODULE_LIST = multiscanner.config.get_modules()
        cls.filelist = utils.parse_dir(os.path.join(CWD, 'files'))

    @classmethod
    def teardown_class(cls):
        multiscanner.config.MODULES_DIR = cls.real_mod_dir
        multiscanner.config.MODULE_LIST = cls.real_mod_list


class TestMultiscan(_runmulti_tests):
    def setup(self):
        multiscanner.config_init(TEST_CONFIG_FILE, multiscanner._get_main_modules())
        multiscanner.update_ms_config_file(TEST_CONFIG_FILE)
        self.result = multiscanner.multiscan(self.filelist)
        self.report = multiscanner.parse_reports(self.result, includeMetadata=False, python=True)
        self.report_m = multiscanner.parse_reports(self.result, includeMetadata=True, python=True)

    def teardown(self):
        os.remove(TEST_CONFIG_FILE)

    def test_multiscan_results(self):
        for f in self.filelist:
            assert f in self.report
            assert f in self.report_m['Files']


class TestMain(_runmulti_tests):
    def setup(self):
        multiscanner.config_init(TEST_CONFIG_FILE, multiscanner._get_main_modules())
        multiscanner.update_ms_config_file(TEST_CONFIG_FILE)
        sys.argv = ['']

    def teardown(self):
        try:
            os.remove(TEST_CONFIG_FILE)
            os.remove(TEST_REPORT)
        except Exception as e:
            # TODO: log exception
            pass

    def test_basic_main(self):
        sys.argv = ['-z', '-j', TEST_REPORT]
        sys.argv.extend(self.filelist)
        multiscanner._main()


class TestMissingConfig(_runmulti_tests):
    def setup(self):
        sys.argv = ['-c', TEST_CONFIG_FILE, 'init']
        multiscanner._main()

    def test_config_init(self):
        config_object = multiscanner.MSConfigParser()
        config_object.read(TEST_CONFIG_FILE)

        assert config_object.has_section('main')
        assert config_object.has_section('test_1')
        assert not config_object.has_section('Cuckoo')

    def test_fill_in_missing_config_sections(self):
        # Simulate a section missing from config file before multiscanner is imported/run
        config_object = multiscanner.MSConfigParser()
        config_object.read(TEST_CONFIG_FILE)
        config_object.remove_section('main')
        config_object.remove_section('test_1')
        with open(TEST_CONFIG_FILE, 'w') as conf_file:
            config_object.write(conf_file)

        # Run MultiScanner
        sys.argv = ['-c', TEST_CONFIG_FILE, os.path.join(CWD, 'files')]
        multiscanner._main()
        with open(TEST_CONFIG_FILE, 'r') as conf_file:
            conf = conf_file.read()
            assert 'test_1' in conf

    def teardown(self):
        os.remove(TEST_CONFIG_FILE)
