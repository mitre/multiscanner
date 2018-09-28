'''
Module for testing the SQLite DB.
Fairly similar to the test_api tests...
'''
import os
import json
import magic
import unittest

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from multiscanner.storage.sql_driver import Database, Task


TEST_DB_PATH = os.path.join(CWD, 'testing.db')
DB_CONF = Database.DEFAULTCONF
DB_CONF['db_name'] = TEST_DB_PATH

# If you want to test with an actual postgres DB server,
# uncomment the following 5 lines and change values accordingly:
# DB_CONF['db_name'] = 'testdb'
# DB_CONF['db_type'] = 'postgresql'
# DB_CONF['host_string'] = 'dbserver.hostname.or.ip'
# DB_CONF['username'] = 'dbusername'
# DB_CONF['password'] = 'dbpassword'


TEST_UPLOAD_FOLDER = os.path.join(CWD, 'tmp')
TEST_TASK = {'task_id': 1, 'task_status': 'Pending', 'timestamp': None, 'sample_id': None}
TEST_REPORT = {'MD5': '96b47da202ddba8d7a6b91fecbf89a41', 'SHA256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f', 'libmagic': 'a /bin/python script text executable', 'filename': '/opt/other_file'}  # noqa: E501


def drop_db_table(db_eng):
    '''
    Cleanup task. Drops the test DB table
    :param db_eng: database engine
    '''
    Task.__table__.drop(db_eng)


class TestTaskSerialization(unittest.TestCase):
    def setUp(self):
        self.task = Task(
            task_id=1,
            task_status='Pending',
            sample_id=None
        )

    def test_task_dict_serialization(self):
        self.assertDictEqual(TEST_TASK, self.task.to_dict())

    def test_task_json_serialization(self):
        task_serialized = json.dumps(TEST_TASK)
        self.assertIn('"task_id": 1', task_serialized)
        self.assertIn('"task_status": "Pending"', task_serialized)
        self.assertIn('"timestamp": null', task_serialized)
        self.assertIn('"sample_id": null', task_serialized)

    def tearDown(self):
        pass


class TestDBInit(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()

    def test_db_init(self):
        if DB_CONF['db_type'] == 'sqlite':
            self.assertIn('SQLite 3.x database', magic.from_file(TEST_DB_PATH))

    def tearDown(self):
        if DB_CONF['db_type'] == 'sqlite':
            os.remove(TEST_DB_PATH)


class TestTaskAdd(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()

    def test_add_task(self):
        task_id = 1
        resp = self.sql_db.add_task(
            task_id=task_id,
            task_status='Pending',
            sample_id=None,
        )
        self.assertEqual(resp, task_id)

    def tearDown(self):
        if DB_CONF['db_type'] == 'sqlite':
            os.remove(TEST_DB_PATH)
        else:
            drop_db_table(self.sql_db.db_engine)


class TestTaskManipulation(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        self.sql_db.add_task(
            task_status='Pending',
        )

    def test_add_second_task(self):
        resp = self.sql_db.add_task()
        self.assertEqual(resp, 2)

    def test_get_task(self):
        resp = self.sql_db.get_task(task_id=1)
        self.assertEqual(resp.task_id, 1)
        self.assertEqual(resp.task_status, 'Pending')
        self.assertEqual(resp.sample_id, None)
        self.assertEqual(resp.timestamp, None)

    def test_update_task(self):
        resp = self.sql_db.update_task(
            task_id=1,
            task_status='Complete',
        )
        self.assertDictEqual(resp, self.sql_db.get_task(1).to_dict())
        self.assertDictEqual(resp, {'task_id': 1, 'sample_id': None, 'task_status': 'Complete', 'timestamp': None})

    def test_delete_task(self):
        deleted = self.sql_db.delete_task(task_id=1)
        self.assertTrue(deleted)
        resp = self.sql_db.get_task(task_id=1)
        self.assertEqual(resp, None)

    def tearDown(self):
        if DB_CONF['db_type'] == 'sqlite':
            os.remove(TEST_DB_PATH)
        else:
            drop_db_table(self.sql_db.db_engine)


class TestGetAllTasks(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        for i in range(0, 3):
            self.sql_db.add_task()
            i += 1

    def test_get_all_tasks(self):
        expected_response = [
            {'task_id': i, 'sample_id': None, 'task_status': 'Pending', 'timestamp': None} for i in range(1, 4)
        ]
        resp = self.sql_db.get_all_tasks()
        for i in range(0, 3):
            self.assertDictEqual(expected_response[i], resp[i])

    def tearDown(self):
        if DB_CONF['db_type'] == 'sqlite':
            os.remove(TEST_DB_PATH)
        else:
            drop_db_table(self.sql_db.db_engine)


class TestStressTest(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        for i in range(0, 1000):
            self.sql_db.add_task()
            i += 1

    def test_get_all_tasks(self):
        for i in range(1, 1000):
            self.sql_db.get_task(task_id=i)

    def tearDown(self):
        if DB_CONF['db_type'] == 'sqlite':
            os.remove(TEST_DB_PATH)
        else:
            drop_db_table(self.sql_db.db_engine)
