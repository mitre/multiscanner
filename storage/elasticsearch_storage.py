'''
Storage module that will interact with elasticsearch.
'''
from uuid import uuid4
from elasticsearch import Elasticsearch, helpers

import storage

class ElasticSearchStorage(storage.Storage):
    '''
    Subclass of Storage.
    '''
    DEFAULTCONF = {
        'ENABLED': True,
        'host': 'localhost',
        'port': 9200,
        'index': 'multiscanner_reports',
        'doc_type': 'reports',
    }

    def setup(self):
        self.host = self.config['host']
        self.port = self.config['port']
        self.index = self.config['index']
        self.doc_type = self.config['doc_type']
        self.es = Elasticsearch(
            host=self.host,
            port=self.port
        )
        return True

    def store(self, report):
        report_id_list = []
        report_list = []

        for filename in report:
            report[filename]['filename'] = filename
            try:
                report_id = report[filename]['SHA256']
            except KeyError:
                report_id = uuid4()
            report_id_list.append(report_id)
            report_list.append(
                {
                    '_index': self.index,
                    '_type': self.doc_type,
                    '_id': report_id,
                    '_source': report[filename]
                }
            )

        result = helpers.bulk(self.es, report_list)
        return report_id_list

    def get_report(self, report_id):
        try:
            result = self.es.get(
                index=self.index, doc_type=self.doc_type,
                id=report_id
            )
            return result['_source']
        except:
            return None

    def delete(self, report_id):
        try:
            self.es.delete(
                index=self.index, doc_type=self.doc_type,
                id=report_id
            )
            return True
        except:
            return False

    def teardown(self):
        pass
