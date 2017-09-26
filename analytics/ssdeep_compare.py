#!/usr/bin/env python

'''
Simple implementation of ssdeep comparisions using
a few optimizations described at the link below.

https://www.virusbulletin.com/virusbulletin/2015/11/optimizing-ssdeep-use-scale
http://www.intezer.com/intezer-community-tip-ssdeep-comparisons-with-elasticsearch/
'''

import sys
import os
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
from elasticsearch_dsl import Search, Q

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
    print('ERROR: This analytic only works with ES stroage module')
    sys.exit(0) 

# probably not ideal...
es = es_handler.es
index = conf['ElasticSearchStorage']['index']
doc_type = 'sample'

# get all of the samples where ssdeep_compare has not been run 
# e.g., ssdeepmeta.analyzed == false
new_ssdeep_searcher = Search(using=es, doc_type=doc_type)

# should probably include some batch functionality to make sure each 
# report has this
q = Q('match', **{ 'ssdeep.analyzed': 'false' })
new_ssdeep_searcher = new_ssdeep_searcher.source(['ssdeep', 'SHA256'])

for new_ssdeep_hit in new_ssdeep_searcher.scan():
    chunksize = new_ssdeep_hit.ssdeep.chunksize
    chunk = new_ssdeep_hit.ssdeep.chunk
    double_chunk = new_ssdeep_hit.ssdeep.double_chunk
    new_sha256 = new_ssdeep_hit.SHA256

    # build new query for docs that match our optimizations
    opti_searcher = Search(using=es, doc_type=doc_type)
    opti_searcher= opti_searcher.source(['ssdeep', 'SHA256'])
    q_chunksize = Q('terms', **{ 'ssdeep.chunksize': [chunksize, chunksize / 2, chunksize * 2] })
    q_chunk_7gram = Q('match', **{ 'ssdeep.chunk': chunk })
    q_double_chunk_7gram = Q('match', **{ 'ssdeep.double_chunk': double_chunk })
    q_diff_sample = ~Q('match', SHA256=new_sha256)
    q = q_chunksize & (q_chunk_7gram | q_double_chunk_7gram) & q_diff_sample
    opti_searcher = opti_searcher.query(q)

    # for each hit, ssdeep.compare != 0; update the matches
    for opti_hit in opti_searcher.scan():
        opti_sha256 = opti_hit.SHA256
        result = ssdeep.compare(
                    new_ssdeep_hit.ssdeep.ssdeep_hash,
                    opti_hit.ssdeep.ssdeep_hash)

        print(new_ssdeep_hit.SHA256, opti_hit.SHA256, result)
        print()

        msg = { 'doc': { 'ssdeep': { 'matches': { opti_sha256: result } } } }
        es.update(
            index=index,
            doc_type=doc_type,
            id=new_ssdeep_hit.meta.id,
            body=json.dumps(msg))

        msg = { 'doc': { 'ssdeep': { 'matches': { new_sha256: result } } } }
        es.update(
            index=index,
            doc_type=doc_type,
            id=opti_hit.meta.id,
            body=json.dumps(msg))

    # analytic has run against sample, set ssdeep.analyzed = true
    msg = { 'doc': { 'ssdeep': { 'analyzed': 'true'} } }
    es.update(
        index=index,
        doc_type=doc_type,
        id=new_ssdeep_hit.meta.id,
        body=json.dumps(msg))

