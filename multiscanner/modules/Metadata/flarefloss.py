# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import subprocess

__author__ = 'Emmanuelle Vargas-Gonzalez'
__license__ = 'MPL 2.0'

TYPE = 'Metadata'
NAME = 'floss'
DEFAULTCONF = {
    'ENABLED': False,
    'path': '/opt/floss',
    'cmdline': [u'--show-metainfo']
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if os.path.isfile(conf['path']):
        return True
    else:
        return False


def scan(filelist, conf=DEFAULTCONF):
    results = []

    for fname in filelist:
        ret = {}
        cmd = _build_command(conf, fname)

        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE)

            for f in p.stdout:
                f = f.decode('utf-8')
                if u'FLOSS static ASCII strings' in f:
                    _extract_data(p.stdout, ret, 'static_ascii_strings')
                elif u'FLOSS static UTF-16 strings' in f:
                    _extract_data(p.stdout, ret, 'static_utf16_strings')
                elif u'stackstrings' in f:
                    _extract_data(p.stdout, ret, 'stack_strings')
                elif u'Vivisect workspace analysis information' in f:
                    _extract_data(p.stdout, ret, 'vivisect_meta_info')
        except subprocess.CalledProcessError as e:
            print(e.stderr)
            print(e)

        if ret:
            results.append((fname, ret))

    metadata = {}
    metadata['Name'] = NAME
    metadata['Type'] = TYPE
    metadata['Include'] = False
    return (results, metadata)


def _build_command(conf, fname):
    cmd = [conf['path'], fname]
    cmd.extend(conf['cmdline'])

    return cmd


def _extract_data(out, ret, key):
    """Sub-routine to extract fragment of console output"""
    ret[key] = []
    feed = next(out, u'').decode('utf-8')
    feed = feed.strip()
    while feed != u'':
        ret[key].append(feed)
        feed = next(out, u'').decode('utf-8')
        feed = feed.strip()

    if not ret[key]:
        del ret[key]
