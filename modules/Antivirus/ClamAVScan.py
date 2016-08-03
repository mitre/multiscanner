# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
try:
    import pyclamd
except:
    print("pyclamd module not installed...")
    pyclamd = None

__author__ = 'Mike Long'
__license__ = "MPL 2.0"

DEFAULTCONF ={
    "ENABLED": True,
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not pyclamd:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []

    try:
        clamScanner = pyclamd.ClamdUnixSocket()
        clamScanner.ping()
    except:
        clamScanner = pyclamd.ClamdNetworkSocket()
        try:
            clamScanner.ping()
        except:
            raise ValueError("Unable to connect to clamd")

    # Scan each file from filelist for virus
    for f in filelist:
        output = clamScanner.scan_file(f)
        if output is None:
            continue

        if list(output.values())[0][0] == 'ERROR':
            with open(f, 'rb') as file_handle:
                try:
                    output = clamScanner.scan_stream(file_handle.read())
                except pyclamd.BufferTooLongError:
                    continue

        if output is None:
            continue

        if list(output.values())[0][0] == 'FOUND':
            results.append((f, list(output.values())[0][1]))
        elif list(output.values())[0][0] == 'ERROR':
            print('ClamAV: ERROR:', list(output.values())[0][1])

    # Set metadata tags
    metadata = {
        'Name': "ClamAV",
        'Type': "Antivirus",
        'Version': clamScanner.version()
    }

    return (results, metadata)
