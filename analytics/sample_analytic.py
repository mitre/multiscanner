#!/usr/bin/env python
import argparse
import json

from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan, bulk

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.externals import joblib


ES_HOSTS = [ 
    'ms-es1.localdomain',
    'ms-es2.localdomain',
    'ms-es3.localdomain',
    'ms-es4.localdomain',
]
ES_INDEX = 'multiscanner_reports'
ES_DOC_TYPE = 'report'

MODEL_FILENAME = 'model.pkl'


def build_feature_dict(report):
    feature_dict = {}

    try:
        task_id = report['Scan Metadata']['Task ID']
    except:
        return None
    try:
        feature_dict['cuckoo_score'] = report['Cuckoo Sandbox']['info']['score']
    except:
        return None
    try:
        feature_dict['cuckoo_num_sigs'] = len(report['Cuckoo Sandbox']['signatures'])
    except:
        feature_dict['cuckoo_num_sigs'] = 0
    try:
        feature_dict['cuckoo_duration'] = report['Cuckoo Sandbox']['info']['duration']
    except:
        return None
    feature_dict['file_entropy'] = report['entropy']
    try:
        feature_dict['num_pe_imports'] = len(report['pefile']['imports'])
    except:
        return None
    try:
        diff = abs(report['pefile']['sections']['_data\x00\x00\x00']['virt_size'] - report['pefile']['sections']['_data\x00\x00\x00']['size'])
        feature_dict['diff_virt_size_real'] = diff
    except Exception as e:
        feature_dict['diff_virt_size_real'] = 0
    try:
        feature_dict['len_floss_strings'] = len(report['floss']['static_ascii_strings'])
    except:
        feature_dict['len_floss_strings'] = 0 

    if task_id <= 500:
        feature_dict['malware'] = False
    elif task_id <= 1000:
        feature_dict['malware'] = True
    else:
        return None
    return feature_dict


def build_feature_dataframe():
    # DataFrame that will hold the feature vector
    es = Elasticsearch(
        hosts=ES_HOSTS
    )

    data_array = []

    report_results = scan(
        es,
        index=ES_INDEX,
        doc_type=ES_DOC_TYPE,
    )

    for result in report_results:
        if 'ERROR' in result['_source'].keys():
            continue

        feature_dict = build_feature_dict(result['_source'])
        if feature_dict:
            data_array.append(feature_dict)
        else:
            continue

    df = pd.DataFrame(data_array)
    # Write the feature array to a file
    # df.to_csv('min_features.csv')
    return df


def build_classifier():
    # df = pd.read_csv('min_features.csv')
    df = build_feature_dataframe()

    feature_cols = ['cuckoo_duration', 'cuckoo_num_sigs', 'cuckoo_score',
       'file_entropy', 'num_pe_imports', 'diff_virt_size_real', 'len_floss_strings']
    X = df.loc[:, feature_cols]

    y = df.malware

    X_train, X_test, y_train, y_test = train_test_split(X, y)

    param_grid = {
        'n_estimators': [10, 100, 500, 1000],
        'max_features': list(range(1, 8))
    }

    forest = GridSearchCV(
        RandomForestClassifier(), param_grid,
        cv=5, n_jobs=-1
    )
    forest.fit(X_train, y_train)
    print('Best params: {}'.format(forest.best_params_))
    print('Performance on test data: {:.4f}'.format(
        forest.score(X_test, y_test)
    ))

    """
    forest = RandomForestClassifier(n_estimators=1000, max_features=2)
    forest.fit(X_train, y_train)

    print('Performance on test data: {:.3f}'.format(forest.score(X_test, y_test)))
    print('\n\nFeature importance:')
    i = 0
    for f in X_train.columns:
        print('{}: {:.3f}'.format(f, forest.feature_importances_[i]))
        i += 1
    print('\n')
    """

    return forest


def label_ms_reports(model):
    es = Elasticsearch(
        hosts=ES_HOSTS
    )
    report_results = scan(
        es,
        index=ES_INDEX,
        doc_type=ES_DOC_TYPE,
    )   
    
    for result in report_results:
        doc_id = result['_id']
        parent = result['_parent']
        feature_dict = build_feature_dict(result['_source'])
        if feature_dict:
            sample_features = [
                [
                    feature_dict.get('cuckoo_duration'),
                    feature_dict.get('cuckoo_num_sigs'),
                    feature_dict.get('cuckoo_score'),
                    feature_dict.get('file_entropy'),
                    feature_dict.get('num_pe_imports'),
                    feature_dict.get('diff_virt_size_real'),
                    feature_dict.get('len_floss_strings'),
                ]
            ]
            prediction = model.predict(sample_features)[0]
            if prediction == True:
                pred = 'Malware'
            else:
                pred = 'Benign'

            b = {'Forest EXE Classifier': pred}
            yield {
                '_op_type': 'update',
                '_index': ES_INDEX,
                '_type': 'report',
                '_id': doc_id,
                '_routing': parent,
                'doc': b
            }


def do_bulk_update(model):
    es = Elasticsearch(
        hosts=ES_HOSTS
    )
    bulk_actions = label_ms_reports(model)
    bulk(
        client=es,
        actions=bulk_actions,
        max_retries=5,
        request_timeout=60
    )


def do_bulk_delete():
    es = Elasticsearch(
        hosts=ES_HOSTS
    )
    bulk_actions = del_model_results()
    bulk(
        client=es,
        actions=bulk_actions,
        max_retries=5,
        request_timeout=60
    )


def del_model_results():
    es = Elasticsearch(
        hosts=ES_HOSTS
    )
    report_results = scan(
        es,
        index=ES_INDEX,
        doc_type=ES_DOC_TYPE,
    ) 
    for result in report_results:
        doc_id = result['_id']
        parent = result['_parent']
        yield {
                '_op_type': 'update',
                '_index': ES_INDEX,
                '_type': 'report',
                '_id': doc_id,
                '_routing': parent,
                'script' : 'ctx._source.remove(\"Forest EXE Classifier\")'
        }


def main():
    parser = argparse.ArgumentParser(description='Classify some malwarez...')
    parser.add_argument(
        '--delete',
        action='store_true',
        default=False,
        help='Delete the classifier results from the MultiScanner reports'
    )
    parser.add_argument(
        '--build',
        action='store_true',
        default=False,
        help='Build a classifier'
    )
    parser.add_argument(
        '--load',
        action='store_true',
        default=False,
        help='Load the classifier'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        default=False,
        help='Save the built classifier'
    )
    parser.add_argument(
        '--index',
        action='store_true',
        default=False,
        help='Update the MultiScanner reports in ElasticSearch with the results from the classifier'
    )
    args = parser.parse_args()

    if args.delete:
        print('Deleting results from previous runs...')
        do_bulk_delete()

    if args.build:
        print('\n\nBuilding model...')
        model = build_classifier()
        if args.save:
            print('\n\nSaving the classifier to file system')
            joblib.dump(model, MODEL_FILENAME)
    elif args.load:
        print('\n\nLoading model...')
        model = joblib.load(MODEL_FILENAME) 
    else:
        model = None
        pass

    if args.index:
        if model:
            print('\n\nUpdating MultiScanner reports...')
            # label_ms_reports(model)
            do_bulk_update(model)
            


if __name__ == '__main__':
    main()
