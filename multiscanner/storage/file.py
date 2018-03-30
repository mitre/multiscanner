import codecs
import gzip
import json

from multiscanner.storage import storage


class File(storage.Storage):
    DEFAULTCONF = {
        'ENABLED': True,
        'path': 'report.json',
        'gzip': False,
        'files-per-line': 1
    }

    def setup(self):
        if self.config['gzip'] is True:
            self.file_handle = gzip.open(self.config['path'], 'a')
        else:
            self.file_handle = codecs.open(self.config['path'], 'ab', 'utf-8')
        return True

    def store(self, results):
        if self.config['files-per-line'] and self.config['files-per-line'] > 0:
            writedata = {}
            metadata = None
            if ['Files', 'Metadata'] == results.keys():
                metadata = results['Metadata']
                results = results['Files']
            i = 0
            for filename in results:
                writedata[filename] = results[filename]
                i += 1
                if i >= self.config['files-per-line']:
                    if metadata:
                        writedata = {'Files': writedata, 'Metadata': metadata}
                    if self.config['gzip'] is True:
                        self.file_handle.write(
                            json.dumps(writedata, sort_keys=True, separators=(',', ':'),
                            ensure_ascii=False).encode('utf8', 'replace'))
                        self.file_handle.write(b'\n')
                    else:
                        self.file_handle.write(
                            json.dumps(writedata, sort_keys=True, separators=(',', ':'),
                            ensure_ascii=False))
                        self.file_handle.write('\n')
                    i = 0
                    writedata = {}
            if writedata:
                if metadata:
                        writedata = {'Files': writedata, 'Metadata': metadata}
                if self.config['gzip'] is True:
                    self.file_handle.write(
                        json.dumps(writedata, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=False).encode('utf8', 'replace'))
                    self.file_handle.write(b'\n')
                else:
                    self.file_handle.write(
                        json.dumps(writedata, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=False))
                    self.file_handle.write('\n')
        else:
            if self.config['gzip'] is True:
                self.file_handle.write(
                    json.dumps(results, sort_keys=True, separators=(',', ':'),
                    ensure_ascii=False).encode('utf8', 'replace'))
                self.file_handle.write(b'\n')
            else:
                self.file_handle.write(
                    json.dumps(results, sort_keys=True, separators=(',', ':'),
                    ensure_ascii=False))
                self.file_handle.write('\n')

    def teardown(self):
        self.file_handle.close()
