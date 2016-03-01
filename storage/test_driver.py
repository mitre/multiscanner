#!/usr/bin/env python

from storage import Storage

NEW_REPORT = {'foo': 'bar', 'boo': 'baz'}

def main():
    db_store = Storage.get_storage()
    for key, value in db_store.__dict__.iteritems():
        print '%s: %s' % (key, value)
    print '\n'

    # report_id = db_store.store(NEW_REPORT)
    report_id = 'AVM0dGOF6iQbRONBw9yB'

    print db_store.get_report(report_id)
    print db_store.get_report(3)

    # db_store.delete(report_id)
    # print db_store.delete(2)



if __name__ == '__main__':
    main()
