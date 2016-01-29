from storage import Storage

class MongoStorage(Storage):
    def __init__(self, config_dict):
        self.db = config_dict['database']
        self.host = config_dict['host']
        self.port = config_dict['port']
        self.username = config_dict['username']
        self.password = config_dict['password']
        self.index = config_dict['index']
        self.doc_type = config_dict['doc_type']

    def store(self, task):
        return 'Task ID'

    def get(self, task_id):
        return {2: {'report': 'data'}}

    def list(self):
        return [{2: {'report': 'data'}}]

    def delete(self, task_id):
        return {'Message': 'deleted'}
