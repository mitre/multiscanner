import json
from storage import Storage

from elasticsearch import Elasticsearch


class ElasticSearchStorage(Storage):
    def __init__(self, config_dict):
        self.db = config_dict['database']
        self.host = config_dict['host']
        self.port = config_dict['port']
        self.username = config_dict['username']
        self.password = config_dict['password']
        self.index = config_dict['index']
        self.doc_type = config_dict['doc_type']
        self.es = Elasticsearch(
            host=self.host,
            port=self.port
        )

    def store(self, report):
        result = self.es.index(
            index=self.index,
            doc_type=self.doc_type,
            body=report
        )
        return result['_id']

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
            result = self.es.delete(
                index=self.index, doc_type=self.doc_type,
                id=report_id
            )
            return True
        except:
            return False
