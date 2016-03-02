#!/usr/bin/env python

from storage import Storage

NEW_REPORT = {'foo': 'bar', 'boo': 'baz'}
REPORTS = {
   "/tmp/example.log": {"MD5": "53f43f9591749b8cae536ff13e48d6de", "SHA256": "815d310bdbc8684c1163b62f583dbaffb2df74b9104e2aadabf8f8491bafab66", "libmagic": "ASCII text"},
   "/opt/other_file": {"MD5": "96b47da202ddba8d7a6b91fecbf89a41", "SHA256": "26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f", "libmagic": "a /bin/python script text executable"},
}

def populate_es():
    db_store = Storage.get_storage()

    return db_store.store(REPORTS)


def main():
    db_store = Storage.get_storage()
    '''
    for key, value in db_store.__dict__.iteritems():
        print '%s: %s' % (key, value)
    print '\n'
    '''

    report_ids = populate_es()

    print db_store.get_report(report_ids[0])
    print db_store.get_report(3)

    db_store.delete(report_ids[0])
    print db_store.delete(2)

    print db_store.get_report(report_ids[0])



if __name__ == '__main__':
    main()
