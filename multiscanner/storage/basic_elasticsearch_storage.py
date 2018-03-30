"""
Storage module that will interact with elasticsearch in a simple way.
"""
from uuid import uuid4

from elasticsearch import Elasticsearch

from multiscanner.storage import storage


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
        self.warned_changed = False
        self.warned_renamed = False
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
            report_data = self.same_type_lists(report_data)
            report_list.append(
                {
                    '_index': self.index,
                    '_type': self.doc_type,
                    '_id': report_id,
                    '_source': report_data
                }
            )

        # result = helpers.bulk(self.es, report_list)
        return report_id_list

    def teardown(self):
        pass

    def dedot(self, dictionary):
        """
        Replaces all dictionary keys with a '.' in them to make Elasticsearch happy
        :param dictionary: The dictionary object
        :return: Dictionary
        """
        for key in dictionary.keys():
            if isinstance(dictionary[key], dict):
                dictionary[key] = self.dedot(dictionary[key])
            if '.' in key:
                new_key = key.replace('.', '_')
                dictionary[new_key] = dictionary[key]
                del dictionary[key]
                if not self.warned_renamed:
                    print('WARNING: Some keys had a . in their name which was replaced with a _')
                    self.warned_renamed = True
        return dictionary

    def same_type_lists(self, dictionary):
        """
        Make sure all lists in a dictionary have elements that are the same type. Otherwise it converts
        them to strings. This does not include list and dict elements.
        :param dictionary: The dictionary object
        :return: Dictionary
        """
        for key in dictionary:
            if isinstance(dictionary[key], list) and dictionary[key]:
                dictionary[key] = self.normalize_list(dictionary[key])
            if isinstance(dictionary[key], dict):
                dictionary[key] = self.same_type_lists(dictionary[key])
        return dictionary

    def check_same_types(self, array):
        """
        Make sure all elements are the same type. This does not include list and dict elements.
        :param array: The list to check
        :return: True or False
        """
        if not array:
            return True
        t = type(array[0])
        for item in array:
            if not isinstance(item, list) and not isinstance(item, dict) and type(item) != t:
                return False
        return True

    def normalize_list(self, array):
        """
        Make sure all elements that are the same type. Otherwise it converts them to strings. This does not include list
        and dict elements.
        :param array: The list to check
        :return: List
        """
        # If we have a list of lists we recurse
        if isinstance(array[0], list):
            for i in range(0, len(array)):
                array[i] = self.normalize_list(array[i])
        # If we have a list of dicts look into them
        elif isinstance(array[0], dict):
            for i in range(0, len(array)):
                array[i] = self.same_type_lists(array[i])
        elif not self.check_same_types(array):
            for i in range(0, len(array)):
                    if isinstance(array[i], list):
                        array[i] = self.normalize_list(array[i])
                    elif isinstance(array[i], dict):
                        array[i] = self.same_type_lists(array[i])
                    else:
                        array[i] = str(array[i])
                        if not self.warned_changed:
                            print("WARNING: We changed some of the data types so that Elasticsearch wouldn't get angry")
                            self.warned_changed = True
        return array
