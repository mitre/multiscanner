from uuid import uuid4
from elasticsearch import Elasticsearch, helpers

from storage import Storage

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
