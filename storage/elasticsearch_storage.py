import json
from storage import Storage

from elasticsearch import Elasticsearch

REPORTS = [
    {'report_id': 1, 'report': {"/tmp/example.log": {"MD5": "53f43f9591749b8cae536ff13e48d6de", "SHA256": "815d310bdbc8684c1163b62f583dbaffb2df74b9104e2aadabf8f8491bafab66", "libmagic": "ASCII text"}}},
    {'report_id': 2, 'report': {"/opt/grep_in_mem.py": {"MD5": "96b47da202ddba8d7a6b91fecbf89a41", "SHA256": "26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f", "libmagic": "a /bin/python script text executable"}}},

]

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
