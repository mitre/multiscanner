'''
Storage module that will interact with elasticsearch.
'''
import os
from datetime import datetime
from uuid import uuid4
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import TransportError
import re
import json

import storage

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


METADATA_FIELDS = [
    'MD5',
    'SHA1',
    'SHA256',
    'ssdeep',
    'tags',
    'Metadata',
]

ES_MAX = 2147483647
CUCKOO_TEMPLATE = os.path.join(MS_WD, 'storage', 'elasticsearch_template.json')
CUCKOO_TEMPLATE_NAME = 'cuckoo_template'


def process_cuckoo_signatures(signatures):
    new_signatures = []

    for signature in signatures:
        new_signature = signature.copy()

        if 'marks' in signature:
            new_signature['marks'] = []
            for mark in signature['marks']:
                new_mark = {}
                for k, v in mark.items():
                    if k != 'call' and type(v) == dict:
                        # If marks is a dictionary we need to explicitly define it for the ES mapping
                        # this is in the case that a key in marks is sometimes a string and sometimes a dictionary
                        # if the first document indexed into ES is a string it will not accept a signature
                        # and through a ES mapping exception.  To counter this dicts will be explicitly stated
                        # in the key except for calls which are always dictionaries.
                        # This presented itself in testing with signatures.marks.section which would sometimes be a
                        # PE section string such as 'UPX'  and other times full details about the section as a
                        # dictionary in the case of packer_upx and packer_entropy signatures
                        new_mark['%s_dict' % k] = v
                    else:
                        # If it is not a mark it is fine to leave key as is
                        new_mark[k] = v

                new_signature['marks'].append(new_mark)

        new_signatures.append(new_signature)

    return new_signatures


class ElasticSearchStorage(storage.Storage):
    '''
    Subclass of Storage.
    '''
    DEFAULTCONF = {
        'ENABLED': False,
        'host': 'localhost',
        'port': 9200,
        'index': 'multiscanner_reports',
        'doc_type': 'report',
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


        # Create the index if it doesn't exist
        es_indices = self.es.indices
        # Add the template for Cuckoo
        with open(CUCKOO_TEMPLATE, 'r') as file_:
            template = json.loads(file_.read())
        if not es_indices.exists_template(CUCKOO_TEMPLATE_NAME):
            es_indices.put_template(
                name=CUCKOO_TEMPLATE_NAME,
                body=json.dumps(template)
            )
        if not es_indices.exists(self.index):
            es_indices.create(self.index)

        # Create parent-child mappings if don't exist yet
        mappings = es_indices.get_mapping(index=self.index)[self.index]['mappings'].keys()
        if self.doc_type not in mappings:
            es_indices.put_mapping(index=self.index, doc_type=self.doc_type, body={
                '_parent': {
                    'type': 'sample'
                }
            })
        if 'note' not in mappings:
            es_indices.put_mapping(index=self.index, doc_type='note', body={
                '_parent': {
                    'type': 'sample'
                },
                'properties': {
                    'timestamp': {
                        'type': 'date',
                    }
                }
            })

        if 'sample' not in mappings:
            es_indices.put_mapping(index=self.index, doc_type='sample', body={
                'properties': {
                    'filename': {
                        'type': 'text'
                    }
                }
            })

        # Create de-dot preprocessor if doesn't exist yet
        try:
            dedot = self.es.ingest.get_pipeline('dedot')
        except TransportError:
            dedot = False
        if not dedot:
            script = {
                "inline": """void dedot(def field) {
                        if (field != null && field instanceof HashMap) {
                            ArrayList replacelist = new ArrayList();
                            for (String key : field.keySet()) {
                                if (key.contains('.')) {
                                    replacelist.add(key)
                                }
                            }
                            for (String oldkey : replacelist) {
                                String newkey = /\\./.matcher(oldkey).replaceAll(\"_\");
                                field.put(newkey, field.get(oldkey));
                                field.remove(oldkey);
                            }
                            for (String k : field.keySet()) {
                                dedot(field.get(k));
                            }
                        }
                    }
                    dedot(ctx);"""
                }
            self.es.ingest.put_pipeline(id='dedot', body={
                'description': 'Replace dots in field names with underscores.',
                'processors': [
                    {
                        "script": script
                    }
                ]
            })

        return True

    def store(self, report):
        sample_ids = {}
        sample_list = []

        for filename in report:
            report[filename]['filename'] = filename
            try:
                sample_id = report[filename]['SHA256']
            except KeyError:
                sample_id = uuid4()
            # Store metadata with the sample, not the report
            sample = {'filename': filename, 'tags': []}
            for field in METADATA_FIELDS:
                if field in report[filename]:
                    if len(report[filename][field]) != 0:
                        sample[field] = report[filename][field]
                    del report[filename][field]

            # If there is Cuckoo results in the report, some
            # cleanup is needed for the report
            if 'Cuckoo Sandbox' in report[filename].keys():
                cuckoo_report = report[filename]['Cuckoo Sandbox']
                cuckoo_doc = {
                    'target': cuckoo_report.get('target'),
                    'summary': cuckoo_report.get('behavior', {}).get('summary'),
                    'info': cuckoo_report.get('info')
                }
                signatures = cuckoo_report.get('signatures')
                if signatures:
                    cuckoo_doc['signatures'] = process_cuckoo_signatures(signatures)

                dropped = cuckoo_report.get('dropped')
                if dropped:
                    cuckoo_doc['dropped'] = dropped

                procmemory = cuckoo_report.get('procmemory')
                if procmemory:
                    cuckoo_doc['procmemory'] = procmemory

                # TODO: add the API calls to the Cuckoo Report document
                # for process in cuckoo_report.get('behavior', {}).get('processes', []):
                #     process_pid = process['pid']
                #     cuckoo_doc['calls'] = {}
                #     cuckoo_doc['calls'][process_pid] = []
                #     for call in process['calls']:
                #         cuckoo_doc['calls'][process_pid].append(call)

                report[filename]['Cuckoo Sandbox'] = cuckoo_doc

            # Store report; let ES autogenerate the ID so we can save it with the sample
            try:
                report_result = self.es.index(index=self.index, doc_type=self.doc_type,
                                              body=report[filename], parent=sample_id,
                                              pipeline='dedot')
            except (TransportError, UnicodeEncodeError) as e:
                # If fail, index empty doc instead
                print('Failed to index that report!\n{}'.format(e))
                report_body_fail = {
                    'ERROR': 'Failed to index the full report in Elasticsearch',
                    'Scan Time': report[filename]['Scan Time']
                }
                report_result = self.es.index(index=self.index, doc_type=self.doc_type,
                                              body=report_body_fail,
                                              parent=sample_id, pipeline='dedot')

            report_id = report_result.get('_id')
            sample['report_id'] = report_id
            sample_ids[sample_id] = report_id

            sample_list.append(
                {
                    '_op_type': 'create',
                    '_index': self.index,
                    '_type': 'sample',
                    '_id': sample_id,
                    '_source': sample,
                    'pipeline': 'dedot'
                }
            )

        result = helpers.bulk(self.es, sample_list, raise_on_error=False)

        creation_errors = result[1]
        if not creation_errors:
            return sample_ids

        # Some samples already exist; update them to ref the new reports
        updates_list = []
        for err in creation_errors:
            if err['create']['status'] == 409:
                sid = err['create']['_id']
                rid = sample_ids[sid]
                updates_list.append(
                    {
                        '_op_type': 'update',
                        '_index': self.index,
                        '_type': 'sample',
                        '_id': sample_id,
                        'doc': {'report_id': rid},
                        'pipeline': 'dedot'
                    }
                )

        result = helpers.bulk(self.es, updates_list, raise_on_error=False)
        return sample_ids

    def get_report(self, sample_id, timestamp):
        '''Find a report for the given sample at the given timestamp, and
        return the report with sample metadata included.
        '''
        ts = str(timestamp).replace(' ', 'T')
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"has_parent": {
                            "parent_type": "sample",
                            "query": {
                                "term": {
                                    "_id": sample_id
                                }
                            }
                        }},
                        {
                            "term": {
                                "Scan Time": ts
                            }
                        }
                    ]
                }
            }
        }

        try:
            result_search = self.es.search(
                index=self.index, doc_type=self.doc_type, body=query
            )
            result_report = result_search['hits']['hits'][0]

            result_sample = self.es.get(
                index=self.index, doc_type='sample',
                id=sample_id
            )
            del result_sample['_source']['report_id']
            result = result_report['_source'].copy()
            result.update(result_sample['_source'])
            return result
        except Exception as e:
            print(e)
            return None

    def build_query(self, query_string):
        return {"query": {"query_string": {
            "default_operator": 'AND',
            "query": query_string}}}

    def search(self, query_string, search_type='default'):
        '''Run a Query String query and return a list of sample_ids associated
        with the matches. Run the query against all document types.
        '''
        print(search_type)
        if search_type == 'advanced':
            query = self.build_query(query_string)
        else:
            es_reserved_chars_re = '([\+\-=\>\<\!\(\)\{\}\[\]\^\"\~\*\?\:\\/ ])'
            query_string = re.sub(es_reserved_chars_re, r'\\\g<1>', query_string)
            print(query_string)
            if search_type == 'default':
                query = self.build_query("*" + query_string + "*")
            elif search_type == 'exact':
                query = self.build_query("\"" + query_string + "\"")
            else:
                print('Unknown search type!')
                return None
        result = helpers.scan(
            self.es, query=query, index=self.index
        )

        matches = []
        for r in result:
            if r['_type'] == 'sample':
                field = '_id'
            else:
                field = '_parent'
            matches.append(r[field])
        return tuple(set(matches))

    def add_tag(self, sample_id, tag):
        script = {
            "script": {
                "inline": "ctx._source.tags.add(params.tag)",
                "lang": "painless",
                "params": {
                    "tag": tag
                }
            }
        }

        try:
            result = self.es.update(
                index=self.index, doc_type='sample',
                id=sample_id, body=script
            )
            return result
        except:
            return None

    def remove_tag(self, sample_id, tag):
        script = {
            "script": {
                "inline": """def i = ctx._source.tags.indexOf(params.tag);
                    if (i > -1) { ctx._source.tags.remove(i); }""",
                "lang": "painless",
                "params": {
                    "tag": tag
                }
            }
        }

        try:
            result = self.es.update(
                index=self.index, doc_type='sample',
                id=sample_id, body=script
            )
            return result
        except:
            return None

    def get_tags(self):
        script = {
            "query": {
                "match_all": {}
            },
            "aggs": {
                "tags_agg": {
                    "terms": {
                        "field": "tags.keyword",
                        "size": ES_MAX
                    }
                }
            }
        }

        result = self.es.search(
            index=self.index, doc_type='sample', body=script
        )
        return result['aggregations']['tags_agg']

    def get_notes(self, sample_id, search_after=None):
        query = {
            "query": {
                "has_parent": {
                    "type": "sample",
                    "query": {
                        "match": {
                            "_id": sample_id
                        }
                    }
                }
            },
            "sort": [
                {
                    "timestamp": {
                        "order": "asc"
                    }
                },
                {
                    "_uid": {
                        "order": "desc"
                    }
                }
            ]
        }
        if search_after:
            query['search_after'] = search_after

        result = self.es.search(
            index=self.index, doc_type='note', body=query
        )
        return result

    def get_note(self, sample_id, note_id):
        try:
            result = self.es.get(
                index=self.index, doc_type='note',
                id=note_id, parent=sample_id
            )
            return result
        except:
            return None

    def add_note(self, sample_id, data):
        data['timestamp'] = datetime.now().isoformat()
        result = self.es.create(
            index=self.index, doc_type='note', id=uuid4(), body=data,
            parent=sample_id
        )
        if result['result'] == 'created':
            return self.get_note(sample_id, result['_id'])
        return result

    def edit_note(self, sample_id, note_id, text):
        partial_doc = {
            "doc": {
                "text": text
            }
        }
        result = self.es.update(
            index=self.index, doc_type='note', id=note_id,
            body=partial_doc, parent=sample_id
        )
        if result['result'] == 'created':
            return self.get_note(sample_id, result['_id'])
        return result

    def delete_note(self, sample_id, note_id):
        result = self.es.delete(
            index=self.index, doc_type='note', id=note_id,
            parent=sample_id
        )
        return result

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
