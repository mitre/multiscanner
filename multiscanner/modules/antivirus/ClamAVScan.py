# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, unicode_literals
import logging

logger = logging.getLogger(__name__)

try:
    import pyclamd
except ImportError:
    logger.error("pyclamd module not installed...")
    pyclamd = None

__author__ = 'Mike Long'
__license__ = "MPL 2.0"

DEFAULTCONF = {
    "ENABLED": False,
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not pyclamd:
        return False
    return True


def _connect_clam():
    try:
        clamScanner = pyclamd.ClamdUnixSocket()
        clamScanner.ping()
    except pyclamd.ConnectionError:
        clamScanner = pyclamd.ClamdNetworkSocket()
        try:
            clamScanner.ping()
        except pyclamd.ConnectionError:
            raise ValueError("Unable to connect to clamd")
    return clamScanner


def scan(filelist, conf=DEFAULTCONF):
    results = []
    try:
        clamScanner = _connect_clam()
    except Exception as e:
        # TODO: log exception
        return None

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
                except Exception as e:
                    logger.error(e)
                    clamScanner = _connect_clam()
                    output = clamScanner.scan_stream(file_handle.read())

        if output is None:
            continue

        if list(output.values())[0][0] == 'FOUND':
            results.append((f, list(output.values())[0][1]))
        elif list(output.values())[0][0] == 'ERROR':
            logger.error('ClamAV: ERROR: {}'.format(list(output.values())[0][1]))

    # Set metadata tags
    metadata = {
        'Name': "ClamAV",
        'Type': "Antivirus",
        'Version': clamScanner.version()
    }

    return (results, metadata)
