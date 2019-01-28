# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
'''
Storage module to interact with MongoDB.
Provides a MongoStorage helper class with the following
functions:
    setup: initialize the Mongo client connection
    store: takes in a report dictionary and posts it to
        mongo instance. Returns a list of report id's.
    get_report: Given a report_id (a sha256 hash), return
        the report.
    delete: Given a report_id (a sha256 hash), delete the
        specified report.
'''
import json
from uuid import uuid4

from pymongo import MongoClient

from multiscanner.storage import storage


class MongoStorage(storage.Storage):
    '''
    Subclass of Storage. Allows user to interact
    with backend Mongo database
    '''
    DEFAULTCONF = {
        'ENABLED': False,
        'host': 'localhost',
        'port': 27017,
        'database': 'multiscanner_reports',
        'collection': 'reports',
    }

    def setup(self):
        self.host = self.config['host']
        self.port = self.config['port']
        self.client = MongoClient(
            host=self.host,
            port=self.port
        )
        self.database = getattr(self.client, self.config['database'])
        self.collection = getattr(self.database, self.config['collection'])
        return True

    def store(self, report):
        report_id_list = []

        for filename in report:
            report[filename]['filename'] = filename
            try:
                report_id = report[filename]['SHA256']
            except KeyError:
                report_id = uuid4()
            report_id_list.append(report_id)

            self.collection.update(
                {'_id': report_id},
                report[filename],
                True
            )

        return report_id_list

    def get_report(self, report_id):
        result = self.collection.find({'_id': report_id})
        if result.count == 0:
            return json.dumps({})
        return json.dumps(result[0])

    def delete(self, report_id):
        result = self.collection.delete_one({'_id': report_id})
        if result.deleted_count == 0:
            return False
        return True
