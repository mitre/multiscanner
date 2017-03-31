import os
import shutil
import sys
import json
try:
    from StringIO import StringIO as BytesIO
except:
    from io import BytesIO
import unittest


CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of api.py
if os.path.join(MS_WD, 'utils') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'utils'))
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

import api
from sql_driver import Database
from storage import Storage


TEST_DB_PATH = os.path.join(CWD, 'testing.db')
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
DB_CONF = Database.DEFAULTCONF
DB_CONF['db_name'] = TEST_DB_PATH

TEST_UPLOAD_FOLDER = os.path.join(CWD, 'tmp')
if not os.path.isdir(TEST_UPLOAD_FOLDER):
    print('Creating upload dir')
    os.makedirs(TEST_UPLOAD_FOLDER)
TEST_REPORT = {'MD5': '96b47da202ddba8d7a6b91fecbf89a41', 'SHA256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f', 'libmagic': 'a /bin/python script text executable', 'filename': '/opt/other_file'}


def post_file(app):
    return app.post(
        '/api/v1/tasks/create/',
        data={'file': (BytesIO(b'my file contents'), 'hello world.txt'),})


def fake_multiscanner_process(file_, original_filename, task_id, report_id):
    pass


class MockStorage(object):
    def get_report(self, report_id):
        return TEST_REPORT

    def delete_report(self, report_id):
        return True


class TestURLCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        self.app = api.app.test_client()
        # Replace the real production DB w/ a testing DB
        api.db = self.sql_db
        api.UPLOAD_FOLDER = TEST_UPLOAD_FOLDER
        if not os.path.isdir(api.UPLOAD_FOLDER):
            os.makedirs(api.UPLOAD_FOLDER)
        api.multiscanner_process = fake_multiscanner_process

    def test_index(self):
        expected_response = {'Message': 'True'}
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_empty_db(self):
        expected_response = {'Tasks': []}
        resp = self.app.get('/api/v1/tasks/list/')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_create_first_task(self):
        expected_response = {'Message': {'task_id': 1}}
        resp = post_file(self.app)
        self.assertEqual(resp.status_code, api.HTTP_CREATED)
        self.assertEqual(json.loads(resp.get_data().decode()), expected_response)

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)
        shutil.rmtree(TEST_UPLOAD_FOLDER)


class TestTaskCreateCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        self.app = api.app.test_client()
        # Replace the real production DB w/ a testing DB
        api.db = self.sql_db
        api.UPLOAD_FOLDER = TEST_UPLOAD_FOLDER
        if not os.path.isdir(api.UPLOAD_FOLDER):
            os.makedirs(api.UPLOAD_FOLDER)
        api.multiscanner_process = fake_multiscanner_process

        # populate the DB w/ a task
        post_file(self.app)

    def test_get_task(self):
        expected_response = {
            'Task': {
                'task_id': 1,
                'task_status': 'Pending',
                'report_id': None
            }
        }
        resp = self.app.get('/api/v1/tasks/list/1')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_get_nonexistent_task(self):
        expected_response = api.TASK_NOT_FOUND
        resp = self.app.get('/api/v1/tasks/list/2')
        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_get_task_list(self):
        expected_response = {'Tasks': [{'task_id': 1, 'task_status': 'Pending', 'report_id': None}]}
        resp = self.app.get('/api/v1/tasks/list/')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)
        shutil.rmtree(TEST_UPLOAD_FOLDER)


class TestTaskUpdateCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        self.app = api.app.test_client()
        # Replace the real production DB w/ a testing DB
        api.db = self.sql_db
        api.UPLOAD_FOLDER = TEST_UPLOAD_FOLDER
        if not os.path.isdir(api.UPLOAD_FOLDER):
            os.makedirs(api.UPLOAD_FOLDER)

        # populate the DB w/ a task
        post_file(self.app)
        self.sql_db.update_task(
            task_id=1,
            task_status='Complete',
            report_id='report1'
        )

    def test_get_updated_task(self):
        expected_response = {
            'Task': {
                'task_id': 1,
                'task_status': 'Complete',
                'report_id': 'report1'
            }
        }
        resp = self.app.get('/api/v1/tasks/list/1')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_delete_nonexistent_task(self):
        expected_response = api.TASK_NOT_FOUND
        resp = self.app.get('/api/v1/tasks/delete/2')
        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)
        shutil.rmtree(TEST_UPLOAD_FOLDER)


class TestTaskDeleteCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        self.app = api.app.test_client()
        # Replace the real production DB w/ a testing DB
        api.db = self.sql_db
        api.UPLOAD_FOLDER = TEST_UPLOAD_FOLDER
        if not os.path.isdir(api.UPLOAD_FOLDER):
            os.makedirs(api.UPLOAD_FOLDER)

        # populate the DB w/ a task
        post_file(self.app)

    def test_delete_task(self):
        expected_response = {'Message': 'Deleted'}
        resp = self.app.get('/api/v1/tasks/delete/1')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_delete_nonexistent_task(self):
        expected_response = api.TASK_NOT_FOUND
        resp = self.app.get('/api/v1/tasks/delete/2')
        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)
        shutil.rmtree(TEST_UPLOAD_FOLDER)


class TestReportCase(unittest.TestCase):
    def setUp(self):
        self.app = api.app.test_client()

    '''
    def test_get_report(self):
        expected_response = {'Report': TEST_REPORT}
        resp = self.app.get('/api/v1/reports/1')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)
    '''

    def test_get_nonexistent_report(self):
        expected_response = api.TASK_NOT_FOUND
        resp = self.app.get('/api/v1/reports/42')
        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def tearDown(self):
        pass
