import os
import shutil
import sys
import json
import mock
import hashlib
try:
    from StringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import unittest


CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of celery_worker.py
if os.path.join(MS_WD, 'utils') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'utils'))
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

import elasticsearch
elasticsearch.client.IndicesClient.exists_template = mock.MagicMock(return_value=True)
elasticsearch.client.IngestClient.get_pipeline = mock.MagicMock(return_value=True)

import celery_worker
import multiscanner
from sql_driver import Database


TEST_DB_PATH = os.path.join(CWD, 'testing.db')
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
DB_CONF = Database.DEFAULTCONF
DB_CONF['db_name'] = TEST_DB_PATH

## Metadata about test file
TEST_FULL_PATH = os.path.join(CWD, 'files/123.txt')
TEST_ORIGINAL_FILENAME = TEST_FULL_PATH.split('/')[-1]
TEST_TASK_ID = 1
with open(TEST_FULL_PATH, 'r') as f:
    TEST_FILE_HASH = hashlib.sha256(f.read().encode('utf-8')).hexdigest()
TEST_METADATA = {}
TEST_CONFIG = multiscanner.CONFIG
FOO_CONFIG = {
    'main': {
        'api-config': 'foo',
        'web-config': 'bar',
        'storage-config': 'baz',
    },
    'libmagic': True,
    'entropy': True,
    'mmbot': False,
    'NSRL': False,
    'fileextensions': False,
    'officemeta': False,
    'ssdeep': False,
}


TEST_REPORT = {
    'MD5': '96b47da202ddba8d7a6b91fecbf89a41',
    'SHA256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f',
    'libmagic': 'a /bin/python script text executable',
    'filename': '/opt/other_file'
}


def post_file(app):
    return app.post(
        '/api/v1/tasks',
        data={'file': (BytesIO(b'my file contents'), 'hello world.txt'), })


# def mock_delay(file_, original_filename, task_id, f_name, metadata, config):
#     return TEST_REPORT


class CeleryTestCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        # Replace the real production DB w/ a testing DB
        celery_worker.db = self.sql_db

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)


class TestCeleryCase(CeleryTestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        # api.multiscanner_celery.delay = mock_delay

    def test_base(self):
        self.assertEqual(True, True)

    @mock.patch('celery_worker.multiscanner_celery')
    def test_success(self, mock_delay):
        mock_delay.return_value = TEST_REPORT
        result = celery_worker.multiscanner_celery(
            file_=TEST_FULL_PATH,
            original_filename=TEST_ORIGINAL_FILENAME,
            task_id=1,
            file_hash=TEST_FILE_HASH,
            metadata=TEST_METADATA,
            config=TEST_CONFIG
        )
        mock_delay.assert_called_once()
        self.assertEqual(result, TEST_REPORT)

    # TODO: patch storage_handler.store(result)
    @mock.patch('celery_worker.multiscanner.storage.StorageHandler')
    def test_delay_method(self, MockStorageHandler):
        result = celery_worker.multiscanner_celery(
            file_=TEST_FULL_PATH,
            original_filename=TEST_ORIGINAL_FILENAME,
            task_id=1,
            file_hash=TEST_FILE_HASH,
            metadata=TEST_METADATA,
            config=FOO_CONFIG
        )
        print(result)
