'''
Module for testing the Elasticsearch datastore.
'''
import os
import sys
import json
import magic
import mock
import unittest
import time

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of elasticsearch_storage
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

# import elasticsearch_storage
from elasticsearch_storage import ElasticSearchStorage



#TEST_DB_PATH = os.path.join(CWD, 'testing.db')
#DB_CONF = Database.DEFAULTCONF
#DB_CONF['db_name'] = TEST_DB_PATH

## If you want to test with an actual postgres DB server,
## uncomment the following 5 lines and change values accordingly:
#DB_CONF['db_name'] = 'testdb'
#DB_CONF['db_type'] = 'postgresql'
#DB_CONF['host_string'] = 'dbserver.hostname.or.ip'
#DB_CONF['username'] = 'dbusername'
#DB_CONF['password'] = 'dbpassword'

#TEST_UPLOAD_FOLDER = os.path.join(CWD, 'tmp')
#TEST_TASK = {'task_id': 1, 'task_status': 'Pending', 'report_id': None, 'sample_id': None}
#TEST_REPORT = {'MD5': '96b47da202ddba8d7a6b91fecbf89a41', 'SHA256': '26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f', 'libmagic': 'a /bin/python script text executable', 'filename': '/opt/other_file'}

#class ESTest(unittest.TestCase):
#class TestES(unittest.TestCase):
#    def setUp(self):
#        # Start ES test server
#        self.es = ElasticSearchServer(cmd="/usr/share/elasticsearch/bin/elasticsearch")
#        print(self.es.arguments)
#        self.es.start()
#        es_test_config = {
#            'host': self.es._bind_host,
#            'port': self.es._bind_port,
#        }
#        self.handler = ElasticSearchStorage(config=es_test_config)
#
#    def test_store(self):
#        resp = self.handler.store(TEST_REPORT)
#        assertEqual(resp, ['26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f'])
#
#    def tearDown(self):
#        # Close ES test server between tests
#        self.es.stop()

TEST_MS_OUTPUT = {'test.txt': {'SHA1': '02bed644797a7adb7d9e3fe8246cc3e1caed0dfe', 'MD5': 'd74129f99f532292de5db9a90ec9d424', 'libmagic': 'ASCII text, with very long lines, with no line terminators', 'ssdeep': '6:BLWw/ELmRCp8o7cu5eul3tkxZBBCGAAIwLE/mUz9kLTCDFM1K7NBVn4+MUq08:4w/ELmR48oJh1exX8G7TW+wM1uFwp', 'SHA256': '03a634eb98ec54d5f7a3c964a82635359611d84dd4ba48e860e6d4817d4ca2a6', 'Metadata': {}}}
TEST_ID = '03a634eb98ec54d5f7a3c964a82635359611d84dd4ba48e860e6d4817d4ca2a6'


class TestES(unittest.TestCase):
    def setUp(self):
        self.handler = ElasticSearchStorage(config=ElasticSearchStorage.DEFAULTCONF)
        self.handler.setup()

    @mock.patch('elasticsearch_storage.helpers')
    def test_store(self, mock_helpers):
        mock_helpers.bulk.return_value = (1, [])
        resp = self.handler.store(TEST_MS_OUTPUT)

        args, kwargs = mock_helpers.bulk.call_args_list[0]
        sample_args = args[1][0]
        self.assertEqual(sample_args['pipeline'], 'dedot')
        self.assertEqual(sample_args['_id'], TEST_ID)
        self.assertEqual(sample_args['_source']['SHA256'], TEST_ID)
        self.assertEqual(sample_args['_source']['tags'], [])

        args, kwargs = mock_helpers.bulk.call_args_list[1]
        report_args = args[1][0]
        self.assertEqual(report_args['_id'], TEST_ID)
        self.assertEqual(report_args['_source']['libmagic'], 'ASCII text, with very long lines, with no line terminators')

        self.assertEqual(resp, [TEST_ID])
        self.assertEqual(mock_helpers.bulk.call_count, 2)

    @mock.patch('elasticsearch_storage.Elasticsearch')
    def test_get_report(self, mock_es):
        resp = self.handler.get_report(TEST_ID, TEST_ID)

        self.assertEqual(mock_es.get.call_count, 2)

    def tearDown(self):
        self.handler.teardown()


#def drop_db_table(db_eng):
#    '''
#    Cleanup task. Drops the test DB table
#    :param db_eng: database engine
#    '''
#    Task.__table__.drop(db_eng)
#
#
#class TestTaskSerialization(unittest.TestCase):
#    def setUp(self):
#        self.task = Task(
#            task_id = 1,
#            task_status = 'Pending',
#            report_id = None,
#            sample_id = None
#        )
#
#    def test_task_dict_serialization(self):
#        self.assertDictEqual(TEST_TASK, self.task.to_dict())
#
#    def test_task_json_serialization(self):
#        task_serialized = json.dumps(TEST_TASK)
#        self.assertIn('"task_id": 1', task_serialized)
#        self.assertIn('"task_status": "Pending"', task_serialized)
#        self.assertIn('"report_id": null', task_serialized)
#        self.assertIn('"sample_id": null', task_serialized)
#
#    def tearDown(self):
#        pass
#
#
#class TestDBInit(unittest.TestCase):
#    def setUp(self):
#        self.sql_db = Database(config=DB_CONF)
#        self.sql_db.init_db()
#
#    def test_db_init(self):
#        if DB_CONF['db_type'] == 'sqlite':
#            self.assertIn('SQLite 3.x database', magic.from_file(TEST_DB_PATH))
#
#    def tearDown(self):
#        if DB_CONF['db_type'] == 'sqlite':
#            os.remove(TEST_DB_PATH)
#
#
#class TestTaskAdd(unittest.TestCase):
#    def setUp(self):
#        self.sql_db = Database(config=DB_CONF)
#        self.sql_db.init_db()
#
#    def test_add_task(self):
#        task_id = 1
#        resp = self.sql_db.add_task(
#            task_id=task_id,
#            task_status='Pending',
#            sample_id=None,
#            report_id=None
#        )
#        self.assertEqual(resp, task_id)
#
#    def tearDown(self):
#        if DB_CONF['db_type'] == 'sqlite':
#            os.remove(TEST_DB_PATH)
#        else:
#            drop_db_table(self.sql_db.db_engine)
#
#
#class TestTaskManipulation(unittest.TestCase):
#    def setUp(self):
#        self.sql_db = Database(config=DB_CONF)
#        self.sql_db.init_db()
#        self.sql_db.add_task(
#            task_status='Pending',
#            report_id=None
#        )
#
#    def test_add_second_task(self):
#        resp = self.sql_db.add_task()
#        self.assertEqual(resp, 2)
#
#    def test_get_task(self):
#        resp = self.sql_db.get_task(task_id=1)
#        self.assertEqual(resp.task_id, 1)
#        self.assertEqual(resp.task_status, 'Pending')
#        self.assertEqual(resp.sample_id, None)
#        self.assertEqual(resp.report_id, None)
#
#    def test_update_task(self):
#        resp = self.sql_db.update_task(
#            task_id=1,
#            task_status='Complete',
#            report_id =  '88d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f'
#        )
#        self.assertDictEqual(resp, self.sql_db.get_task(1).to_dict())
#        self.assertDictEqual(resp, {'task_id': 1, 'sample_id': None, 'task_status': 'Complete', 'report_id': '88d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f'})
#
#    def test_delete_task(self):
#        deleted = self.sql_db.delete_task(task_id=1)
#        self.assertTrue(deleted)
#        resp = self.sql_db.get_task(task_id=1)
#        self.assertEqual(resp, None)
#
#    def tearDown(self):
#        if DB_CONF['db_type'] == 'sqlite':
#            os.remove(TEST_DB_PATH)
#        else:
#            drop_db_table(self.sql_db.db_engine)
#
#
#class TestGetAllTasks(unittest.TestCase):
#    def setUp(self):
#        self.sql_db = Database(config=DB_CONF)
#        self.sql_db.init_db()
#        for i in range(0,3):
#            self.sql_db.add_task()
#            i += 1
#
#    def test_get_all_tasks(self):
#        expected_response = [
#            {'task_id': i, 'sample_id': None, 'task_status': 'Pending', 'report_id': None} for i in range(1,4)
#        ]
#        resp = self.sql_db.get_all_tasks()
#        for i in range(0,3):
#            self.assertDictEqual(expected_response[i], resp[i])
#
#    def tearDown(self):
#        if DB_CONF['db_type'] == 'sqlite':
#            os.remove(TEST_DB_PATH)
#        else:
#            drop_db_table(self.sql_db.db_engine)
#
#
#class TestStressTest(unittest.TestCase):
#    def setUp(self):
#        self.sql_db = Database(config=DB_CONF)
#        self.sql_db.init_db()
#        for i in range(0,1000):
#            self.sql_db.add_task()
#            i += 1
#
#    def test_get_all_tasks(self):
#        for i in range(1,1000):
#            self.sql_db.get_task(task_id=i)
#
#    def tearDown(self):
#        if DB_CONF['db_type'] == 'sqlite':
#            os.remove(TEST_DB_PATH)
#        else:
#            drop_db_table(self.sql_db.db_engine)
