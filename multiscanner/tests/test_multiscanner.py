from __future__ import division, absolute_import, print_function, unicode_literals
import os
import sys

import multiscanner
from multiscanner.common import utils

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))


class _runmulti_tests(object):
    @classmethod
    def setup_class(cls):
        cls.real_mod_dir = multiscanner.MODULES_DIR
        multiscanner.MODULES_DIR = os.path.join(CWD, "modules")
        cls.filelist = utils.parse_dir(os.path.join(CWD, 'files'))
        config_file = '.tmpfile.ini'
        multiscanner.config_init(config_file)
        multiscanner.update_ms_config_file(config_file)

    @classmethod
    def teardown_class(cls):
        multiscanner.MODULES_DIR = cls.real_mod_dir


class Test_multiscan(_runmulti_tests):
    def setup(self):
        self.result = multiscanner.multiscan(self.filelist)
        self.report = multiscanner.parse_reports(self.result, includeMetadata=False, python=True)
        self.report_m = multiscanner.parse_reports(self.result, includeMetadata=True, python=True)

    def teardown(self):
        os.remove('.tmpfile.ini')

    def test_multiscan_results(self):
        for f in self.filelist:
            assert f in self.report
            assert f in self.report_m['Files']


class Test_main(_runmulti_tests):
    def setup(self):
        sys.argv = ['']

    def teardown(self):
        try:
            os.remove('.tmpfile.ini')
            os.remove('tmp_report.json')
        except Exception as e:
            # TODO: log exception
            pass

    def test_basic_main(self):
        sys.argv = ['-z', '-j', 'tmp_report.json']
        sys.argv.extend(self.filelist)
        multiscanner._main()
