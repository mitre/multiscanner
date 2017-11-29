# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import sys
import requests

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "VirusTotal"
VT_URL = 'https://www.virustotal.com/vtapi/v2/file/report'
VT_HASH_LIMIT = 25
REQUIRES = ["MD5"]
DEFAULTCONF = {
    'apikey': None,
    'ENABLED': True
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if None in REQUIRES:
        return False
    if not conf['apikey']:
        return False
    if not conf['allinfo']:
        conf['allinfo'] = 0
    return True


def scan(filelist, conf=DEFAULTCONF):
    md5_tuples, junk = REQUIRES[0]
    apikey = conf['apikey']
    all_hashes = [md5[1] for md5 in md5_tuples]

    # Virustotals API limits the number of hashes per request to 25 - sublists of len <=25 are created
    hash_lists = [all_hashes[i:i + VT_HASH_LIMIT] for i in range(0, len(all_hashes), VT_HASH_LIMIT)]

    # Check for key rotation
    rotkey = False
    if isinstance(apikey, list):
        rotkey = _repeatlist(apikey)
        apikey = rotkey.next()

    jdata = []
    for hash_list in hash_lists:
        params = {'resource': ', '.join(hash_list),
                  'apikey': apikey,
                  'allinfo': conf['allinfo']}

        response = _send_vt_request(params, rotkey)
        jdata = jdata + response.json()

    results = list(_generate_results(jdata, md5_tuples))

    metadata = {"Name": NAME,
                "Type": TYPE,
                "Include": False}

    return (results, metadata)


def _send_vt_request(params, rotkey):
    try:
        response = requests.get(VT_URL, params=params)

        if response.status_code == 200:
            return response

        if response.status_code == 403 and rotkey:
            try:
                params['apikey'] = rotkey.next()
                _send_vt_request(params, rotkey)

            except:
                print("ERROR: No more VirusTotal API keys to try")
                sys.exit(1)
        else:
            print("ERROR: Invalid VirusTotal API key")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print("ERROR: VirusTotal connection failure: " + str(e))
        sys.exit(1)


def _generate_results(jdata, md5_tuples):
    if not isinstance(jdata, list):
        jdata = [jdata]

    for report in jdata:
        if report['response_code'] == 1:

            # get filename using hash as the lookup key
            filename = [v[0] for i, v in enumerate(md5_tuples) if v[1] == report['md5']][0]

            del report['response_code']
            del report['verbose_msg']

            yield (filename, report)


def _repeatlist(data):
    while True:
        for d in data:
            yield d
