#!/usr/bin/env python

from storage import Storage

# STORAGE_CONFIG = '/opt/multiscanner/config_storage.ini'

def main():
    db_store = Storage.get_storage()
    for key, value in db_store.__dict__.iteritems():
        print '%s: %s' % (key, value)

    print '\n'
    print db_store.get_report(1)


if __name__ == '__main__':
    main()
