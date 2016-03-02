from storage import Storage

TASKS = [
    {'task_id': 1, 'task_status': 'Complete', 'report_id': 1},
    {'task_id': 2, 'task_status': 'Pending', 'report_id': None},
]
REPORTS = [
    {'report_id': 1, 'report': {"/tmp/example.log": {"MD5": "53f43f9591749b8cae536ff13e48d6de", "SHA256": "815d310bdbc8684c1163b62f583dbaffb2df74b9104e2aadabf8f8491bafab66", "libmagic": "ASCII text"}}},
    {'report_id': 2, 'report': {"/opt/grep_in_mem.py": {"MD5": "96b47da202ddba8d7a6b91fecbf89a41", "SHA256": "26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f", "libmagic": "a /bin/python script text executable"}}},
]

class MongoStorage(Storage):
    def __init__(self, config_dict):
        self.db = config_dict['database']
        self.host = config_dict['host']
        self.port = config_dict['port']
        self.username = config_dict['username']
        self.password = config_dict['password']
        self.index = config_dict['index']
        self.doc_type = config_dict['doc_type']

    def store(self, report):
        report_id = REPORTS[-1]['report_id'] + 1 
        REPORTS.append({'report_id': report_id, 'report': report})
        return report_id

    def get_report(self, report_id):
        report = [report for report in REPORTS if report['report_id'] == report_id]
        if len(report) == 0:
            return {}
        return json.dumps(report[0])

    def delete(self, report_id):
        report = [report for report in REPORTS if report['report_id'] == report_id]
        if len(report) == 0:
            return False
        REPORTS.remove(report[0])
        return True
