'''
Module for testing the Elasticsearch datastore.
'''
import os
import mock
import unittest

from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient, IngestClient

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from multiscanner.storage.elasticsearch_storage import ElasticSearchStorage

TEST_MS_OUTPUT = {'test.txt': {'SHA1': '02bed644797a7adb7d9e3fe8246cc3e1caed0dfe', 'MD5': 'd74129f99f532292de5db9a90ec9d424', 'libmagic': 'ASCII text, with very long lines, with no line terminators', 'ssdeep': '6:BLWw/ELmRCp8o7cu5eul3tkxZBBCGAAIwLE/mUz9kLTCDFM1K7NBVn4+MUq08:4w/ELmR48oJh1exX8G7TW+wM1uFwp', 'SHA256': '03a634eb98ec54d5f7a3c964a82635359611d84dd4ba48e860e6d4817d4ca2a6', 'Metadata': {}, "Scan Time": "2017-09-26T16:48:05.395004"}}    # noqa: E501
TEST_ID = '03a634eb98ec54d5f7a3c964a82635359611d84dd4ba48e860e6d4817d4ca2a6'
TEST_NOTE_ID = 'eba3d3de-1a7e-4018-8fb3-a4635b4b7ab1'
TEST_TS = "2017-09-26T16:48:05.395004"


class TestES(unittest.TestCase):
    @mock.patch.object(IndicesClient, 'exists_template')
    @mock.patch.object(IngestClient, 'get_pipeline')
    def setUp(self, mock_pipe, mock_exists):
        mock_pipe.return_value = True
        mock_exists.return_value = True
        self.handler = ElasticSearchStorage(config=ElasticSearchStorage.DEFAULTCONF)
        self.handler.setup()

    @mock.patch.object(Elasticsearch, 'index')
    @mock.patch('multiscanner.storage.elasticsearch_storage.helpers')
    def test_store(self, mock_helpers, mock_index):
        mock_helpers.bulk.return_value = (1, [])
        resp = self.handler.store(TEST_MS_OUTPUT)

        args, kwargs = mock_helpers.bulk.call_args_list[0]
        sample_args = args[1][0]
        self.assertEqual(sample_args['pipeline'], 'dedot')
        self.assertEqual(sample_args['_id'], TEST_ID)
        self.assertEqual(sample_args['_source']['SHA256'], TEST_ID)
        self.assertEqual(sample_args['_source']['tags'], [])

        report_args, report_kwargs = mock_index.call_args_list[0]
        self.assertEqual(report_kwargs['routing'], TEST_ID)
        self.assertEqual(
            report_kwargs['body']['libmagic'],
            'ASCII text, with very long lines, with no line terminators')
        self.assertEqual(report_kwargs['pipeline'], 'dedot')

        self.assertIn(TEST_ID, resp)

    @mock.patch.object(Elasticsearch, 'search')
    @mock.patch.object(Elasticsearch, 'get')
    def test_get_report(self, mock_get, mock_search):
        self.handler.get_report(TEST_ID, TEST_TS)

        args, kwargs = mock_search.call_args_list[0]
        self.assertEqual(kwargs['index'], ElasticSearchStorage.DEFAULTCONF['index'])
        self.assertEqual(kwargs['body']['query']['bool']['must'][0]['parent_id']['type'], 'report')
        self.assertEqual(kwargs['body']['query']['bool']['must'][0]['parent_id']['id'], TEST_ID)
        self.assertEqual(kwargs['body']['query']['bool']['must'][1]['term']['Scan Metadata.Scan Time'], TEST_TS)
        self.assertEqual(kwargs['doc_type'], '_doc')

        mock_get.assert_any_call(index=ElasticSearchStorage.DEFAULTCONF['index'], id=TEST_ID, doc_type='_doc')

    @mock.patch('multiscanner.storage.elasticsearch_storage.helpers')
    def test_search(self, mock_helpers):
        mock_helpers.scan.return_value = [{'sort': [417], '_type': '_doc', '_routing': TEST_ID, '_index': 'multiscanner_reports', '_score': None, '_source': {'libmagic': 'ASCII text, with very long lines, with no line terminators', 'filename': 'test.txt', 'doc_type': {'name': 'report', 'parent': TEST_ID}}, '_id': TEST_ID}]     # noqa: E501
        resp = self.handler.search('test')

        args, kwargs = mock_helpers.scan.call_args_list[0]
        query = kwargs['query']
        self.assertEqual(query['query']['query_string']['query'], '*test*')

        self.assertEqual(resp, (TEST_ID,))

    @mock.patch.object(Elasticsearch, 'update')
    def test_add_tag(self, mock_update):
        self.handler.add_tag(TEST_ID, 'foo')

        args, kwargs = mock_update.call_args_list[0]
        doc_type = kwargs['doc_type']
        sample_id = kwargs['id']
        body = str(kwargs['body'])

        self.assertEqual(mock_update.call_count, 1)
        self.assertEqual(doc_type, '_doc')
        self.assertEqual(sample_id, TEST_ID)
        assert 'ctx._source.tags.add(params.tag)' in body
        assert "'tag': 'foo'" in body

    @mock.patch.object(Elasticsearch, 'update')
    def test_remove_tag(self, mock_update):
        self.handler.remove_tag(TEST_ID, 'foo')

        args, kwargs = mock_update.call_args_list[0]
        doc_type = kwargs['doc_type']
        sample_id = kwargs['id']
        body = str(kwargs['body'])

        self.assertEqual(mock_update.call_count, 1)
        self.assertEqual(doc_type, '_doc')
        self.assertEqual(sample_id, TEST_ID)
        assert 'ctx._source.tags.remove(' in body
        assert "'tag': 'foo'" in body

    @mock.patch.object(Elasticsearch, 'search')
    def test_get_tags(self, mock_search):
        mock_search.return_value = {"aggregations": {
            "tags_agg": {
                "doc_count_error_upper_bound": 0,
                "sum_other_doc_count": 0,
                "buckets": [
                    {
                        "key": "Malicious",
                        "doc_count": 1
                    },
                    {
                        "key": "Benign",
                        "doc_count": 1
                    }
                ]
            }
        }}
        tag_1 = mock_search.return_value['aggregations']['tags_agg']['buckets'][0]
        tag_2 = mock_search.return_value['aggregations']['tags_agg']['buckets'][1]
        resp = self.handler.get_tags()

        self.assertEqual(mock_search.call_count, 1)
        args, kwargs = mock_search.call_args_list[0]
        query = kwargs['body']
        doc_type = kwargs['doc_type']

        self.assertEqual(doc_type, '_doc')
        self.assertEqual(query['aggs']['tags_agg']['terms']['field'], 'tags.keyword')
        self.assertEqual(resp[0], tag_1)
        self.assertEqual(resp[1], tag_2)

    @mock.patch.object(Elasticsearch, 'search')
    def test_get_notes(self, mock_search):
        self.handler.get_notes(TEST_ID)

        self.assertEqual(mock_search.call_count, 1)
        args, kwargs = mock_search.call_args_list[0]
        doc_type = kwargs['doc_type']
        query = kwargs['body']

        self.assertEqual(doc_type, '_doc')
        self.assertEqual(query['query']['parent_id']['type'], 'note')
        self.assertEqual(query['query']['parent_id']['id'], TEST_ID)

    @mock.patch.object(Elasticsearch, 'get')
    def test_get_note(self, mock_get):
        self.handler.get_note(TEST_ID, TEST_ID)

        self.assertEqual(mock_get.call_count, 1)
        args, kwargs = mock_get.call_args_list[0]
        doc_type = kwargs['doc_type']
        sample_id = kwargs['routing']
        note_id = kwargs['id']

        self.assertEqual(doc_type, '_doc')
        self.assertEqual(sample_id, TEST_ID)
        self.assertEqual(note_id, TEST_ID)

    @mock.patch.object(Elasticsearch, 'get')
    @mock.patch.object(Elasticsearch, 'index')
    def test_add_note(self, mock_index, mock_get):
        mock_index.return_value = {'result': 'created', '_id': TEST_ID}
        self.handler.add_note(TEST_ID, {'text': 'foo'})

        self.assertEqual(mock_index.call_count, 1)
        args, kwargs = mock_index.call_args_list[0]
        doc_type = kwargs['doc_type']
        parent = kwargs['routing']
        body = kwargs['body']

        self.assertEqual(doc_type, '_doc')
        self.assertEqual(parent, TEST_ID)
        self.assertEqual(body['text'], 'foo')
        self.assertEqual(mock_get.call_count, 1)

    @mock.patch.object(Elasticsearch, 'update')
    def test_edit_note(self, mock_update):
        mock_update.return_value = {'result': 'success', '_id': TEST_ID}
        self.handler.edit_note(TEST_ID, TEST_NOTE_ID, 'foo')

        self.assertEqual(mock_update.call_count, 1)
        args, kwargs = mock_update.call_args_list[0]
        doc_type = kwargs['doc_type']
        note_id = kwargs['id']
        parent = kwargs['routing']
        body = kwargs['body']
        print(body)

        self.assertEqual(doc_type, '_doc')
        self.assertEqual(parent, TEST_ID)
        self.assertEqual(note_id, TEST_NOTE_ID)
        self.assertEqual(body['doc']['text'], 'foo')

    @mock.patch.object(Elasticsearch, 'delete')
    def test_delete_note(self, mock_delete):
        self.handler.delete_note(TEST_ID, TEST_NOTE_ID)

        self.assertEqual(mock_delete.call_count, 1)
        args, kwargs = mock_delete.call_args_list[0]
        doc_type = kwargs['doc_type']
        parent = kwargs['routing']
        note_id = kwargs['id']

        self.assertEqual(doc_type, '_doc')
        self.assertEqual(parent, TEST_ID)
        self.assertEqual(note_id, TEST_NOTE_ID)

    @mock.patch.object(Elasticsearch, 'delete')
    def test_delete(self, mock_delete):
        self.handler.delete(TEST_ID)

        self.assertEqual(mock_delete.call_count, 1)
        args, kwargs = mock_delete.call_args_list[0]
        doc_type = kwargs['doc_type']
        report_id = kwargs['id']

        self.assertEqual(doc_type, '_doc')
        self.assertEqual(report_id, TEST_ID)

    def tearDown(self):
        self.handler.teardown()
