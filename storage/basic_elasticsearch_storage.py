"""
Storage module that will interact with elasticsearch in a simple way.
"""
from uuid import uuid4
from elasticsearch import Elasticsearch, helpers
import storage


class BasicElasticSearchStorage(storage.Storage):
    DEFAULTCONF = {
        'ENABLED': False,
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
            report_data = self.dedot(report[filename])
            report_list.append(
                {
                    '_index': self.index,
                    '_type': self.doc_type,
                    '_id': report_id,
                    '_source': report_data
                }
            )

        result = helpers.bulk(self.es, report_list)
        return report_id_list

    def teardown(self):
        pass

    def dedot(self, dictonary):
        for key in dictonary.keys():
            if isinstance(dictonary[key], dict):
                dictonary[key] = self.dedot(dictonary[key])
            if '.' in key:
                new_key = key.replace('.', '_')
                dictonary[new_key] = dictonary[key]
                del dictonary[key]
        return dictonary
