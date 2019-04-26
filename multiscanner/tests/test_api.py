import os
import shutil
import json
import mock
try:
    from StringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import unittest

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from multiscanner.distributed import api
from multiscanner.storage.sql_driver import Database

import elasticsearch
elasticsearch.client.IndicesClient.exists_template = mock.MagicMock(return_value=True)
elasticsearch.client.IngestClient.get_pipeline = mock.MagicMock(return_value=True)

TEST_DB_PATH = os.path.join(CWD, 'testing.db')
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
DB_CONF = Database.DEFAULTCONF
DB_CONF['db_name'] = TEST_DB_PATH

TEST_UPLOAD_FOLDER = os.path.join(CWD, 'tmp')
if not os.path.isdir(TEST_UPLOAD_FOLDER):
    os.makedirs(TEST_UPLOAD_FOLDER)
api.api_config['api']['upload_folder'] = TEST_UPLOAD_FOLDER

TEST_REPORT = {
    'MD5': '96b47da202ddba8d7a6b91fecbf89a41',
    'SHA256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f',
    'libmagic': 'a /bin/python script text executable',
    'filename': '/opt/other_file'
}


def post_file(app):
    return app.post(
        '/api/v2/tasks',
        data={'file': (BytesIO(b'my file contents'), 'hello world.txt'), })


def mock_apply_async(args, kwargs, **options):
    pass


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.sql_db = Database(config=DB_CONF)
        self.sql_db.init_db()
        self.app = api.app.test_client()
        # Replace the real production DB w/ a testing DB
        api.db = self.sql_db
        if not os.path.isdir(TEST_UPLOAD_FOLDER):
            os.makedirs(TEST_UPLOAD_FOLDER)

    def tearDown(self):
        # Clean up Test DB and upload folder
        os.remove(TEST_DB_PATH)
        shutil.rmtree(TEST_UPLOAD_FOLDER)


class TestURLCase(APITestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        api.multiscanner_celery.apply_async = mock_apply_async

    def test_index(self):
        expected_response = {'Message': True}
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_empty_db(self):
        expected_response = []
        resp = self.app.get('/api/v2/tasks')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_create_first_task(self):
        expected_response = [1]
        resp = post_file(self.app)
        self.assertEqual(resp.status_code, api.HTTP_CREATED)
        self.assertEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_get_modules(self):
        resp = self.app.get('/api/v2/modules').get_data().decode('utf-8')
        self.assertTrue(len(json.loads(resp).keys()) > 1)


class TestTaskCreateCase(APITestCase):
    def setUp(self):
        super(self.__class__, self).setUp()

        # populate the DB w/ a task
        post_file(self.app)

    def test_get_task(self):
        expected_response = {
            'task_id': 1,
            'task_status': 'Pending',
            'sample_id': '114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9',
            'timestamp': None,
        }
        resp = self.app.get('/api/v2/tasks/1')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_get_nonexistent_task(self):
        expected_response = api.TASK_NOT_FOUND
        resp = self.app.get('/api/v2/tasks/2')
        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_get_task_list(self):
        expected_response = [{
            'task_id': 1,
            'task_status': 'Pending',
            'sample_id': '114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9',
            'timestamp': None,
        }]
        resp = self.app.get('/api/v2/tasks')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertEqual(json.loads(resp.get_data().decode()), expected_response)


class TestTaskUpdateCase(APITestCase):
    def setUp(self):
        super(self.__class__, self).setUp()

        # populate the DB w/ a task
        post_file(self.app)
        self.sql_db.update_task(
            task_id=1,
            task_status='Complete',
        )

    def test_get_updated_task(self):
        expected_response = {
            'task_id': 1,
            'task_status': 'Complete',
            'sample_id': '114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9',
            'timestamp': None,
        }
        resp = self.app.get('/api/v2/tasks/1')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)


class TestTaskDeleteCase(APITestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        # populate the DB w/ a task
        post_file(self.app)

    @mock.patch('multiscanner.distributed.api.handler')
    def test_delete_task(self, mock_handler):
        mock_handler.delete_by_task_id.return_value = True
        expected_response = {'Message': True}
        resp = self.app.delete('/api/v2/tasks/1')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    @mock.patch('multiscanner.distributed.api.handler')
    def test_delete_nonexistent_task(self, mock_handler):
        mock_handler.delete_by_task_id.return_value = False
        expected_response = api.TASK_NOT_FOUND
        resp = self.app.delete('/api/v2/tasks/2')
        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)


class TestReportCase(APITestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        # populate the DB w/ a task
        post_file(self.app)
        self.sql_db.update_task(
            task_id=1,
            task_status='Complete',
        )

    @mock.patch('multiscanner.distributed.api.handler')
    def test_get_report(self, mock_handler):
        mock_handler.get_report.return_value = TEST_REPORT
        expected_response = TEST_REPORT
        resp = self.app.get('/api/v2/tasks/1/report')
        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    def test_get_nonexistent_report(self):
        expected_response = api.TASK_NOT_FOUND
        resp = self.app.get('/api/v2/tasks/42/report')
        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)
        self.assertDictEqual(json.loads(resp.get_data().decode()), expected_response)

    @mock.patch('multiscanner.distributed.api.db')
    @mock.patch('multiscanner.distributed.api.handler')
    def test_search_analyses(self, mock_handler, mock_db):
        mock_handler.search.return_value = [1]
        self.app.get('/api/v2/tasks/_datatable?search[value]=other_file')

        hargs, hkwargs = mock_handler.search.call_args_list[0]
        self.assertEqual(hargs[0], 'other_file')
        self.assertEqual(hargs[1], 'default')

        dbargs, dbkwargs = mock_db.search.call_args_list[0]
        self.assertEqual(dbargs[0]['search[value]'], 'other_file')
        self.assertEqual(dbargs[1], [1])

    @mock.patch('multiscanner.distributed.api.db')
    @mock.patch('multiscanner.distributed.api.handler')
    def test_search_history(self, mock_handler, mock_db):
        mock_handler.search.return_value = [1]
        self.app.get('/api/v2/tasks/_datatable/history?search[value]=other_file')

        hargs, hkwargs = mock_handler.search.call_args_list[0]
        self.assertEqual(hargs[0], 'other_file')
        self.assertEqual(hargs[1], 'default')

        dbargs, dbkwargs = mock_db.search.call_args_list[0]
        self.assertEqual(dbargs[0]['search[value]'], 'other_file')
        self.assertEqual(dbargs[1], [1])
        self.assertEqual(dbkwargs['return_all'], True)


class TestTagsNotesCase(APITestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        # populate the DB w/ a task
        post_file(self.app)
        self.sql_db.update_task(
            task_id=1,
            task_status='Complete',
        )

    @mock.patch('multiscanner.distributed.api.handler')
    def test_add_tags(self, mock_handler):
        self.app.post('/api/v2/tasks/1/tags', data={'tag': 'foo'})

        args, kwargs = mock_handler.add_tag.call_args_list[0]
        self.assertEqual(args[1], 'foo')

    @mock.patch('multiscanner.distributed.api.handler')
    def test_remove_tags(self, mock_handler):
        self.app.delete('/api/v2/tasks/1/tags', data={'tag': 'foo'})

        args, kwargs = mock_handler.remove_tag.call_args_list[0]
        self.assertEqual(args[0], '114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9')
        self.assertEqual(args[1], 'foo')

    @mock.patch('multiscanner.distributed.api.handler')
    def test_add_notes(self, mock_handler):
        self.app.post('/api/v2/tasks/1/notes', data={'text': 'foo'})

        args, kwargs = mock_handler.add_note.call_args_list[0]
        self.assertEqual(args[0], '114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9')
        self.assertEqual(args[1]['text'], 'foo')

    @mock.patch('multiscanner.distributed.api.handler')
    def test_edit_notes(self, mock_handler):
        self.app.put('/api/v2/tasks/1/notes/KNeQuWcBTlckoQ5PFm4B', data={'text': 'bar'})

        args, kwargs = mock_handler.edit_note.call_args_list[0]
        self.assertEqual(args[0], '114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9')
        self.assertEqual(args[1], 'KNeQuWcBTlckoQ5PFm4B')
        self.assertEqual(args[2], 'bar')

    @mock.patch('multiscanner.distributed.api.handler')
    def test_remove_notes(self, mock_handler):
        self.app.delete('/api/v2/tasks/1/notes/KNeQuWcBTlckoQ5PFm4B')

        args, kwargs = mock_handler.delete_note.call_args_list[0]
        self.assertEqual(args[0], '114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9')
        self.assertEqual(args[1], 'KNeQuWcBTlckoQ5PFm4B')


class TestSHA256DownloadSampleCase(APITestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        # populate the DB w/ a task
        post_file(self.app)
        self.sql_db.update_task(
            task_id=1,
            task_status='Complete',
        )

    @mock.patch('multiscanner.distributed.api.db')
    @mock.patch('multiscanner.distributed.api.handler')
    def test_malformed_request(self, mock_handler, mock_db):
        resp = self.app.get(r'/api/v2/files/..\opt\multiscanner\web_config.ini')

        self.assertEqual(resp.status_code, api.HTTP_BAD_REQUEST)

    @mock.patch('multiscanner.distributed.api.db')
    @mock.patch('multiscanner.distributed.api.handler')
    def test_other_hash(self, mock_handler, mock_db):
        # using MD5 instead of SHA256
        resp = self.app.get('/api/v2/files/96b47da202ddba8d7a6b91fecbf89a41')

        self.assertEqual(resp.status_code, api.HTTP_BAD_REQUEST)

    @mock.patch('multiscanner.distributed.api.db')
    @mock.patch('multiscanner.distributed.api.handler')
    def test_file_download_raw(self, mock_handler, mock_db):
        expected_response = b'my file contents'
        resp = self.app.get('/api/v2/files/114d70ba7d04c76d8c217c970f99682025c89b1a6ffe91eb9045653b4b954eb9?raw=t')

        self.assertEqual(resp.status_code, api.HTTP_OK)
        self.assertEqual(resp.get_data(), expected_response)

    @mock.patch('multiscanner.distributed.api.db')
    @mock.patch('multiscanner.distributed.api.handler')
    def test_file_not_found(self, mock_handler, mock_db):
        resp = self.app.get('/api/v2/files/26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f?raw=t')

        self.assertEqual(resp.status_code, api.HTTP_NOT_FOUND)


class TestCeleryPriorityQueues(APITestCase):

    def mock_async_call(self, args, kwargs, **options):
        priority = options.get('priority', 5)

        if 1 <= priority <= 3:
            self.low_tasks.append((priority, [args, kwargs, options]))
        elif 4 <= priority <= 7:
            self.medium_tasks.append((priority, [args, kwargs, options]))
        elif 8 <= priority <= 10:
            self.high_tasks.append((priority, [args, kwargs, options]))

    def setUp(self):
        super(TestCeleryPriorityQueues, self).setUp()
        self.high_tasks = []
        self.medium_tasks = []
        self.low_tasks = []
        api.multiscanner_celery.apply_async = self.mock_async_call

    def test_priority_queue_high(self):
        # populate the DB w/ a task
        self.app.post(
            '/api/v2/tasks',
            data={'file': (BytesIO(b'my file contents'), 'hello world.txt'), 'priority': 10}
        )

        self.assertEqual(len(self.high_tasks), 1)

    def test_priority_queue_medium(self):
        # populate the DB w/ a task
        self.app.post(
            '/api/v2/tasks',
            data={'file': (BytesIO(b'my file contents'), 'hello world.txt'), 'priority': 5}
        )

        self.assertEqual(len(self.medium_tasks), 1)

    def test_priority_queue_low(self):
        # populate the DB w/ a task
        self.app.post(
            '/api/v2/tasks',
            data={'file': (BytesIO(b'my file contents'), 'hello world.txt'), 'priority': 1}
        )

        self.assertEqual(len(self.low_tasks), 1)
