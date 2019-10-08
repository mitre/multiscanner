import hashlib
import os
import unittest

import mock
import multiscanner

from multiscanner.distributed import celery_worker
from multiscanner.storage.sql_driver import Database

try:
    from StringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO


CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get a subset of simple modules to run in testing
# the celery worker
MODULES_TO_TEST = [
    'filemeta',
    'ssdeep'
]


TEST_DB_PATH = os.path.join(CWD, 'testing.db')
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
DB_CONF = Database.DEFAULTCONF
DB_CONF['db_name'] = TEST_DB_PATH

# Metadata about test file
TEST_FULL_PATH = os.path.join(CWD, 'files/123.txt')
TEST_ORIGINAL_FILENAME = TEST_FULL_PATH.split('/')[-1]
TEST_TASK_ID = 1
with open(TEST_FULL_PATH, 'r') as f:
    TEST_FILE_HASH = hashlib.sha256(f.read().encode('utf-8')).hexdigest()
TEST_METADATA = {}
TEST_CONFIG = multiscanner.config.MS_CONFIG

TEST_REPORT = {
    'filemeta': {
        'entropy': 2.0,
        'md5': '96b47da202ddba8d7a6b91fecbf89a41',
        'sha256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f',
        'filetype': 'a /bin/python script text executable',
    },
    'filename': '/opt/other_file'
}


def post_file(app):
    return app.post(
        '/api/v1/tasks',
        data={'file': (BytesIO(b'my file contents'), 'hello world.txt'), })


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

    def test_base(self):
        self.assertEqual(True, True)

    @mock.patch('multiscanner.distributed.celery_worker.multiscanner_celery')
    def test_success(self, mock_apply_async):
        mock_apply_async.return_value = TEST_REPORT
        result = celery_worker.multiscanner_celery(
            file_=TEST_FULL_PATH,
            original_filename=TEST_ORIGINAL_FILENAME,
            task_id=1,
            file_hash=TEST_FILE_HASH,
            metadata=TEST_METADATA,
            config=TEST_CONFIG
        )
        mock_apply_async.assert_called_once()
        self.assertEqual(result, TEST_REPORT)

    # Patch storage_handler.store(result) inside the celery_worker module
    # prevents indexing test reports into ES or other side effects
    @mock.patch('multiscanner.distributed.celery_worker.storage.StorageHandler')
    def test_delay_method(self, MockStorageHandler):
        expected_entropy = 2.0
        expected_MD5 = 'ba1f2511fc30423bdbb183fe33f3dd0f'
        expected_SHA1 = 'a8fdc205a9f19cc1c7507a60c4f01b13d11d7fd0'
        expected_SHA256 = '181210f8f9c779c26da1d9b2075bde0127302ee0e3fca38c9a83f5b1dd8e5d3b'
        expected_filetype = 'ASCII text'

        # run the multiscanner celery worker on our test file
        result = celery_worker.multiscanner_celery(
            file_=TEST_FULL_PATH,
            original_filename=TEST_ORIGINAL_FILENAME,
            task_id=1,
            file_hash=TEST_FILE_HASH,
            metadata=TEST_METADATA,
            module_list=MODULES_TO_TEST
        )

        self.assertEqual(
            result.get(TEST_ORIGINAL_FILENAME, {}).get('filemeta', {}).get('entropy'),
            expected_entropy
        )
        self.assertEqual(
            result.get(TEST_ORIGINAL_FILENAME, {}).get('filemeta', {}).get('md5'),
            expected_MD5
        )
        self.assertEqual(
            result.get(TEST_ORIGINAL_FILENAME, {}).get('filemeta', {}).get('sha1'),
            expected_SHA1
        )
        self.assertEqual(
            result.get(TEST_ORIGINAL_FILENAME, {}).get('filemeta', {}).get('sha256'),
            expected_SHA256
        )
        self.assertEqual(
            result.get(TEST_ORIGINAL_FILENAME, {}).get('filemeta', {}).get('filetype'),
            expected_filetype
        )
