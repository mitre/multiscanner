#!/usr/bin/env python

'''
Simple implementation of ssdeep comparisions using a few optimizations
described at the links below

https://www.virusbulletin.com/virusbulletin/2015/11/optimizing-ssdeep-use-scale
http://www.intezer.com/intezer-community-tip-ssdeep-comparisons-with-elasticsearch/

Designed to be run on a regular basis (e.g., nightly).

For each sample that has not run ssdeep analytic, search for samples where
ssdeep.compare > 0 based on chunksize, chunk 7grams, and double-chunk 7grams.
Update sample with any matches and mark ssdeep analytic as having run
'''

import sys
import os
import argparse
import requests
import json
import ssdeep
import configparser

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
if MS_WD not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD))

import multiscanner
import common
import elasticsearch_storage


def main():
    parser = argparse.ArgumentParser(description='Script to interact with Multiscanner\'s '
        'Elasticsearch datastore to run ssdeep.compare using a few '
        'optimizations based on ssdeep hash structure.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='Increase output to stdout')
    args = parser.parse_args()

    storage_conf = multiscanner.common.get_config_path(multiscanner.CONFIG, 'storage')
    config_object = configparser.SafeConfigParser()
    config_object.optionxform = str
    config_object.read(storage_conf)
    conf = common.parse_config(config_object)
    storage_handler = multiscanner.storage.StorageHandler(configfile=storage_conf)
    es_handler = None
    for handler in storage_handler.loaded_storage:
        if isinstance(handler, elasticsearch_storage.ElasticSearchStorage):
            es_handler = handler
            break

    if not es_handler:
        print('[!] ERROR: This analytic only works with ES stroage module.')
        sys.exit(0)

    # probably not ideal...
    ES = es_handler.es
    INDEX = conf['ElasticSearchStorage']['index']
    DOC_TYPE = 'sample'

    # get all of the samples where ssdeep_compare has not been run
    # e.g., ssdeepmeta.analyzed == false
    query = {
        '_source': ['ssdeep', 'SHA256'],
        'query': {
            'bool': {
                'must': [
                    { 'match': { 'ssdeep.analyzed': 'false' }}
                ]
            }
        }
    }

    page = ES.search(
        INDEX,
        scroll='2m',
        size=1000,
        body=query)

    records_list = []
    while len(page['hits']['hits']) > 0:
        for hit in page['hits']['hits']:
            records_list.append(hit)
        sid = page['_scroll_id']
        page = ES.scroll(scroll_id=sid, scroll='2m')

    for new_ssdeep_hit in records_list:
        new_ssdeep_hit_src = new_ssdeep_hit.get('_source')
        chunksize = new_ssdeep_hit_src.get('ssdeep').get('chunksize')
        chunk = new_ssdeep_hit_src.get('ssdeep').get('chunk')
        double_chunk = new_ssdeep_hit_src.get('ssdeep').get('double_chunk')
        new_sha256 = new_ssdeep_hit_src.get('SHA256')

        # build new query for docs that match our optimizations
        # https://github.com/intezer/ssdeep-elastic/blob/master/ssdeep_elastic/ssdeep_querying.py#L35
        opti_query = {
            '_source': ['ssdeep', 'SHA256'],
            'query': {
                'bool': {
                    'must': [
                        {
                            'terms': {
                                'ssdeep.chunksize': [chunksize, chunksize / 2, chunksize * 2]
                            }
                        },
                        {
                            'bool': {
                                'should': [
                                    {
                                        'match': {
                                            'ssdeep.chunk': {
                                                'query': chunk
                                            }
                                        }
                                    },
                                    {
                                        'match': {
                                            'ssdeep.double_chunk': {
                                                'query': double_chunk
                                            }
                                        }
                                    }
                                ],
                                'minimum_should_match': 1
                            }
                        },
                        {
                            'bool': {
                                'must_not': {
                                    'match': {
                                        'SHA256': new_sha256
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }

        # this bool condition isn't working how I expect
        #   if we have already updated the match dictionary to
        #   include a hit, don't rerun it for the inverse
                        # {
                        #     'bool': {
                        #         'must_not': {
                        #             'exists': {
                        #                 'field': 'ssdeep.matches.' + new_sha256
                        #             }
                        #         }
                        #     }
                        # }

        opti_page = ES.search(
            INDEX,
            scroll='2m',
            size=1000,
            body=opti_query)

        while len(opti_page['hits']['hits']) > 0:
            # for each hit, ssdeep.compare != 0; update the matches
            for opti_hit in opti_page['hits']['hits']:
                opti_hit_src = opti_hit.get('_source')
                opti_sha256 = opti_hit_src.get('SHA256')
                result = ssdeep.compare(
                            new_ssdeep_hit_src.get('ssdeep').get('ssdeep_hash'),
                            opti_hit_src.get('ssdeep').get('ssdeep_hash'))

                if args.verbose:
                    print(
                        new_ssdeep_hit_src.get('SHA256'),
                        opti_hit_src.get('SHA256'),
                        result)

                msg = { 'doc': { 'ssdeep': { 'matches': { opti_sha256: result } } } }
                ES.update(
                    index=INDEX,
                    doc_type=DOC_TYPE,
                    id=new_ssdeep_hit.get('_id'),
                    body=json.dumps(msg))

                msg = { 'doc': { 'ssdeep': { 'matches': { new_sha256: result } } } }
                ES.update(
                    index=INDEX,
                    doc_type=DOC_TYPE,
                    id=opti_hit.get('_id'),
                    body=json.dumps(msg))

                opti_sid = opti_page['_scroll_id']
                opti_page = ES.scroll(scroll_id=opti_sid, scroll='2m')

        # analytic has run against sample, set ssdeep.analyzed = true
        msg = { 'doc': { 'ssdeep': { 'analyzed': 'true'} } }
        ES.update(
            index=INDEX,
            doc_type=DOC_TYPE,
            id=new_ssdeep_hit.get('_id'),
            body=json.dumps(msg))

if __name__ == '__main__':
    main()
