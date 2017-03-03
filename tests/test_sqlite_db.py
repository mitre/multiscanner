'''
Module for testing the SQLite DB.
Fairly similar to the test_api tests...
'''
import os
import sys
import json
import magic
import unittest

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of sqlite_driver
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

from sqlite_driver import Database, Task


TEST_DB_PATH = os.path.join(CWD, 'testing.db')
TEST_UPLOAD_FOLDER = os.path.join(CWD, 'tmp')
TEST_TASK = {'task_id': 1, 'task_status': 'Pending', 'report_id': None}
TEST_REPORT = {'MD5': '96b47da202ddba8d7a6b91fecbf89a41', 'SHA256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f', 'libmagic': 'a /bin/python script text executable', 'filename': '/opt/other_file'}


class TestTaskSerialization(unittest.TestCase):
    def setUp(self):
        self.task = Task(
            task_id = 1,
            task_status = 'Pending',
            report_id = None
        )

    def test_task_dict_serialization(self):
        self.assertDictEqual(TEST_TASK, self.task.to_dict())

    def test_task_json_serialization(self):
        self.assertEqual(
            json.dumps(TEST_TASK), self.task.to_json()
        )

    def tearDown(self):
        pass


class TestDBInit(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(TEST_DB_PATH)
        self.sql_db.init_sqlite_db()

    def test_db_init(self):
        self.assertIn('SQLite 3.x database', magic.from_file(TEST_DB_PATH))

    def tearDown(self):
        os.remove(TEST_DB_PATH)


class TestTaskAdd(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(TEST_DB_PATH)
        self.sql_db.init_sqlite_db()

    def test_add_task(self):
        task_id = 1
        resp = self.sql_db.add_task(
            task_id=task_id,
            task_status='Pending',
            report_id=None
        )
        self.assertEqual(resp, task_id)

    def tearDown(self):
        os.remove(TEST_DB_PATH)


class TestTaskManipulation(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(TEST_DB_PATH)
        self.sql_db.init_sqlite_db()
        self.sql_db.add_task(
            task_id=1,
            task_status='Pending',
            report_id=None
        )

    def test_add_second_task(self):
        resp = self.sql_db.add_task()
        self.assertEqual(resp, 2)

    def test_get_task(self):
        resp = self.sql_db.get_task(task_id=1)
        self.assertEqual(resp.task_id, 1)
        self.assertEqual(resp.task_status, 'Pending')
        self.assertEqual(resp.report_id, None)

    def test_update_task(self):
        resp = self.sql_db.update_task(
            task_id=1,
            task_status='Complete',
            report_id =  '88d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f'
        )
        self.assertDictEqual(resp, self.sql_db.get_task(1).to_dict())
        self.assertDictEqual(resp, {'task_id': 1, 'task_status': 'Complete', 'report_id': '88d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f'})

    def test_delete_task(self):
        deleted = self.sql_db.delete_task(task_id=1)
        self.assertTrue(deleted)
        resp = self.sql_db.get_task(task_id=1)
        self.assertEqual(resp, None)

    def tearDown(self):
        os.remove(TEST_DB_PATH)


class TestGetAllTasks(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(TEST_DB_PATH)
        self.sql_db.init_sqlite_db()
        for i in range(0,3):
            self.sql_db.add_task()
            i += 1

    def test_get_all_tasks(self):
        expected_response = [
            {'task_id': i, 'task_status': 'Pending', 'report_id': None} for i in range(1,4)
        ]
        resp = self.sql_db.get_all_tasks()
        for i in range(0,3):
            self.assertDictEqual(expected_response[i], resp[i])

    def tearDown(self):
        os.remove(TEST_DB_PATH)
