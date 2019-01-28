'''
Storage module that will interact with elasticsearch.
'''
import json
import logging
import os
import re
from datetime import datetime
from uuid import uuid4

import curator

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import TransportError

from multiscanner import MS_WD
from multiscanner.storage import storage

METADATA_FIELDS = [
    'MD5',
    'SHA1',
    'SHA256',
    'ssdeep',
    'tags',
    'Metadata',
]

ES_MAX = 2147483647
ES_TEMPLATE = os.path.join(MS_WD, 'storage', 'templates', 'elasticsearch_template.json')
ES_TEMPLATE_NAME = 'multiscanner_template'


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
        'metricbeat_enabled': True,
        'metricbeat_rollover_days': 7,
    }

    def setup(self):
        host_string = self.config['host']
        host_list = []
        for host in host_string.split(','):
            host_list.append(host.strip(' '))
        self.hosts = host_list
        self.port = self.config['port']
        self.index = self.config['index']
        self.doc_type = '_doc'
        self.es = Elasticsearch(
            hosts=self.hosts,
            port=self.port
        )

        # Reduce traceback output from the elasticsearch module
        es_logger = logging.getLogger('elasticsearch')
        es_logger.setLevel(logging.ERROR)

        # Create the index if it doesn't exist
        es_indices = self.es.indices
        # Add the template for Cuckoo
        with open(ES_TEMPLATE, 'r') as file_:
            template = json.loads(file_.read())
        if not es_indices.exists_template(ES_TEMPLATE_NAME):
            es_indices.put_template(
                name=ES_TEMPLATE_NAME,
                body=json.dumps(template)
            )

        # Try to create the index, pass if it exists
        try:
            es_indices.create(self.index)
        except TransportError:
            pass

        # Set the total fields limit
        try:
            es_indices.put_settings(
                index=self.index,
                body={'index.mapping.total_fields.limit': ES_MAX},
            )
        except TransportError:
            pass

        # Create de-dot preprocessor if doesn't exist yet
        try:
            dedot = self.es.ingest.get_pipeline('dedot')
        except TransportError:
            dedot = False
        if not dedot:
            script = {
                "source": """void dedot(def field) {
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
        sample_tags = {}  # track in case we need to update sample instead of create

        for filename in report:
            report[filename]['filename'] = filename
            try:
                sample_id = report[filename]['SHA256']
            except KeyError:
                sample_id = uuid4()
            # Store metadata with the sample, not the report
            sample = {'doc_type': 'sample', 'filename': filename, 'tags': []}
            for field in METADATA_FIELDS:
                if field in report[filename]:
                    if len(report[filename][field]) != 0:
                        sample[field] = report[filename][field]
                    del report[filename][field]
            report[filename]['doc_type'] = {'name': 'report', 'parent': sample_id}
            sample_tags[sample_id] = sample.get('tags', [])

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
                                              body=report[filename],
                                              pipeline='dedot', routing=sample_id)
            except (TransportError, UnicodeEncodeError) as e:
                # If fail, index empty doc instead
                print('Failed to index that report!\n{}'.format(e))
                report_body_fail = {
                    'doc_type': {
                        'name': 'report',
                        'parent': sample_id,
                    },
                    'ERROR': 'Failed to index the full report in Elasticsearch',
                }
                if 'Scan Time' in report[filename]:
                    report_body_fail['Scan Time'] = report[filename]['Scan Time']
                report_result = self.es.index(index=self.index, doc_type=self.doc_type,
                                              body=report_body_fail,
                                              pipeline='dedot', routing=sample_id)

            report_id = report_result.get('_id')
            sample['report_id'] = report_id
            sample_ids[sample_id] = report_id

            sample_list.append(
                {
                    '_op_type': 'create',
                    '_index': self.index,
                    '_type': self.doc_type,
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
                        '_type': self.doc_type,
                        '_id': sid,
                        'doc': {'report_id': rid},
                        'pipeline': 'dedot'
                    }
                )
                # Update tags
                for tag in sample_tags.get(sid, []):
                    self.add_tag(sid, tag)

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
                        {"parent_id": {
                            "type": "report",
                            "id": sample_id
                        }},
                        {
                            "term": {
                                "Scan Metadata.Scan Time": ts
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
                index=self.index, doc_type=self.doc_type,
                id=sample_id
            )
            del result_sample['_source']['report_id']
            del result_sample['_source']['doc_type']
            del result_report['_source']['doc_type']
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
        if search_type == 'advanced':
            query = self.build_query(query_string)
        else:
            es_reserved_chars_re = r'([\+\-=\>\<\!\(\)\{\}\[\]\^\"\~\*\?\:\\/ ])'
            query_string = re.sub(es_reserved_chars_re, r'\\\g<1>', query_string)
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
            if r.get('_source', {}).get('doc_type', {}) == 'sample':
                field = '_id'
            else:
                field = '_routing'
            matches.append(r[field])
        return tuple(set(matches))

    def add_tag(self, sample_id, tag):
        script = {
            "script": {
                "inline": """def i = ctx._source.tags.indexOf(params.tag);
                    if (i == -1) { ctx._source.tags.add(params.tag); }""",
                "lang": "painless",
                "params": {
                    "tag": tag
                }
            }
        }

        try:
            result = self.es.update(
                index=self.index, doc_type=self.doc_type,
                id=sample_id, body=script
            )
            return result
        except Exception as e:
            # TODO: log exception
            return None

    def remove_tag(self, sample_id, tag):
        script = {
            "script": {
                "source": """def i = ctx._source.tags.indexOf(params.tag);
                    if (i > -1) { ctx._source.tags.remove(i); }""",
                "lang": "painless",
                "params": {
                    "tag": tag
                }
            }
        }

        try:
            result = self.es.update(
                index=self.index, doc_type=self.doc_type,
                id=sample_id, body=script
            )
            return result
        except Exception as e:
            # TODO: log exception
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
            index=self.index, doc_type=self.doc_type, body=script
        )
        return result['aggregations']['tags_agg']['buckets']

    def get_notes(self, sample_id, search_after=None):
        query = {
            "query": {
                "parent_id": {
                    "type": "note",
                    "id": sample_id
                }
            },
            "sort": [
                {
                    "timestamp": {
                        "order": "asc"
                    }
                },
                {
                    "_id": {
                        "order": "desc"
                    }
                }
            ]
        }
        if search_after:
            query['search_after'] = search_after

        result = self.es.search(
            index=self.index, doc_type=self.doc_type, body=query
        )
        return result

    def get_note(self, sample_id, note_id):
        try:
            result = self.es.get(
                index=self.index, doc_type=self.doc_type,
                id=note_id, routing=sample_id
            )
            return result
        except Exception as e:
            # TODO: log exception
            return None

    def add_note(self, sample_id, data):
        data['doc_type'] = {'name': 'note', 'parent': sample_id}
        data['timestamp'] = datetime.now().isoformat()
        result = self.es.index(
            index=self.index, doc_type=self.doc_type, body=data,
            routing=sample_id
        )
        if result['result'] == 'created':
            return self.get_note(sample_id, result['_id'])
        return result

    def edit_note(self, sample_id, note_id, text):
        partial_doc = {
            'doc': {
                "text": text
            }
        }
        print(partial_doc)
        result = self.es.update(
            index=self.index, doc_type=self.doc_type, id=note_id,
            body=partial_doc, routing=sample_id
        )
        if result['result'] == 'created':
            return self.get_note(sample_id, result['_id'])
        return result

    def delete_note(self, sample_id, note_id):
        result = self.es.delete(
            index=self.index, doc_type=self.doc_type, id=note_id,
            routing=sample_id
        )
        return result

    def delete(self, report_id):
        try:
            self.es.delete(
                index=self.index, doc_type=self.doc_type,
                id=report_id
            )
            return True
        except Exception as e:
            # TODO: log exception
            return False

    def delete_by_task_id(self, task_id):
        query = {
            "query": {
                "term": {
                    "Scan Metadata.Task ID": task_id
                }
            }
        }

        try:
            self.es.delete_by_query(
                index=self.index, doc_type=self.doc_type, body=query
            )
            return True
        except Exception as e:
            # TODO: log exception
            return False

    def teardown(self):
        pass

    def delete_index(self, index_prefix, days):
        '''
        Delete index equal to or older than days.
        '''
        try:
            ilo = curator.IndexList(self.es)
            ilo.filter_by_regex(kind='prefix', value=index_prefix)
            ilo.filter_by_age(source='name', direction='older', timestring='%Y.%m.%d', unit='days', unit_count=days)
            delete_indices = curator.DeleteIndices(ilo)
            delete_indices.do_action()
        except Exception as e:
            # TODO: log exception
            return False
