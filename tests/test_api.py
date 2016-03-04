import os
import time
import shutil
import sys
import json
import responses
import unittest
from StringIO import StringIO

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of api.py
if os.path.join(MS_WD, 'utils') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'utils'))
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

import multiscanner
import api
from sqlite_driver import Database


TEST_DB_PATH = os.path.join(CWD, 'testing.db')
TEST_UPLOAD_FOLDER = os.path.join(CWD, 'tmp')

HTTP_OK = 200
HTTP_CREATED = 201


def post_file(app):
    return app.post(
        '/api/v1/tasks/create/',
        data={'file': (StringIO('my file contents'), 'hello world.txt'),})



class TestURLCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(TEST_DB_PATH)
        self.sql_db.init_sqlite_db()
        self.app = api.app.test_client()
        # Replace the real production DB w/ a testing DB
        api.db = self.sql_db
        api.UPLOAD_FOLDER = TEST_UPLOAD_FOLDER
        if not os.path.isdir(api.UPLOAD_FOLDER):
            os.makedirs(api.UPLOAD_FOLDER)
        

    def test_index(self):
        expected_response = {'Message': 'True'}
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, HTTP_OK)
        self.assertEqual(json.loads(resp.data), expected_response)

    def test_empty_db(self):
        expected_response = {'Tasks': []}
        resp = self.app.get('/api/v1/tasks/list/')
        self.assertEqual(resp.status_code, HTTP_OK)
        self.assertEqual(json.loads(resp.data), expected_response)

    def test_create_first_task(self):
        expected_response = {'Message': {'task_id': 1}}
        resp = post_file(self.app)
        self.assertEqual(resp.status_code, HTTP_CREATED)
        self.assertEqual(json.loads(resp.data), expected_response)

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)
        shutil.rmtree(TEST_UPLOAD_FOLDER)


class TestTaskCreateCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(TEST_DB_PATH)
        self.sql_db.init_sqlite_db()
        self.app = api.app.test_client()
        # Replace the real production DB w/ a testing DB
        api.db = self.sql_db
        api.UPLOAD_FOLDER = TEST_UPLOAD_FOLDER
        if not os.path.isdir(api.UPLOAD_FOLDER):
            os.makedirs(api.UPLOAD_FOLDER)

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
        self.assertEqual(resp.status_code, HTTP_OK)
        self.assertDictEqual(json.loads(resp.data), expected_response)

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)
        shutil.rmtree(TEST_UPLOAD_FOLDER)
