'''
Module for testing the SQLite DB.
Fairly similar to the test_api tests...
'''
import os
import sys
import json
import unittest

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of sqlite_driver
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

from sqlite_driver import Database, Record


TEST_DB_PATH = os.path.join(CWD, 'testing.db')
TEST_UPLOAD_FOLDER = os.path.join(CWD, 'tmp')
TEST_RECORD = {'task_id': 1, 'task_status': 'Pending', 'report_id': None}
TEST_REPORT = {'MD5': '96b47da202ddba8d7a6b91fecbf89a41', 'SHA256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f', 'libmagic': 'a /bin/python script text executable', 'filename': '/opt/other_file'}


class TestRecordSerialization(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(TEST_DB_PATH)
        self.sql_db.init_sqlite_db()
        self.record = Record(
            task_id = 1,
            task_status = 'Pending',
            report_id = None
        )

    def test_record_dict_serialization(self):
        self.assertDictEqual(TEST_RECORD, self.record.to_dict())

    def test_record_json_serialization(self):
        self.assertEqual(
            json.dumps(TEST_RECORD), self.record.to_json())

    def tearDown(self):
        os.remove(TEST_DB_PATH)
