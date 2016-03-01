#!/usr/bin/env python

from storage import Storage

NEW_REPORT = {'foo': 'bar', 'boo': 'baz'}

def main():
    db_store = Storage.get_storage()
    for key, value in db_store.__dict__.iteritems():
        print '%s: %s' % (key, value)
    print '\n'

    db_store.store(NEW_REPORT)

    print db_store.get_report(2)
    print db_store.get_report(3)

    db_store.delete(2)
    print db_store.delete(2)


if __name__ == '__main__':
    main()
