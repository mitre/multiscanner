import storage
import gzip
import json
import codecs


class File(storage.Storage):
    DEFAULTCONF = {
        'ENABLED': True,
        'path': 'report.json',
        'gzip': False,
        'files-per-line': 1
    }

    def setup(self):
        if self.config['gzip'] is True:
            self.file_handle = gzip.open(self.config['path'], 'ab')
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
                    self.file_handle.write(json.dumps(writedata, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8', errors='replace'))
                    self.file_handle.write('\n')
                    i = 0
                    writedata = {}
            if writedata:
                if metadata:
                        writedata = {'Files': writedata, 'Metadata': metadata}
                self.file_handle.write(json.dumps(writedata, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8', errors='replace'))
                self.file_handle.write('\n')

        else:
            self.file_handle.write(json.dumps(results, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8', errors='replace'))
            self.file_handle.write('\n')

    def teardown(self):
        self.file_handle.close()
