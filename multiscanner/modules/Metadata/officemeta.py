# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import (absolute_import, division, unicode_literals, with_statement)

import binascii
import logging
from builtins import *  # noqa 401,403

from multiscanner.ext.office_meta import OfficeParser

__author__ = "Patrick Coplenad"
__credits__ = ["Mike Goffin"]
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "officemeta"
REQUIRES = ["filemeta"]
DEFAULTCONF = {
    'ENABLED': True,
}

logger = logging.getLogger(__name__)


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if None in REQUIRES:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []
    filemeta_results, _ = REQUIRES[0]
    for fname, filemeta_result in filemeta_results:
        # TODO: better office doc detection
        if filemeta_result.get('filetype', '').startswith('Composite Document') or True:
            ret = None
            try:
                with open(fname, 'rb') as fh:
                    ret = run(fh.read())
            except Exception as e:
                logger.exception(e)
            if ret:
                results.append((fname, ret))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)


def run(data):
    ret = {}
    ret['directory'] = {}
    # ret['doc_meta'] = []
    ret['doc_meta'] = {}
    oparser = OfficeParser(data)
    oparser.parse_office_doc()
    if not oparser.office_header.get('maj_ver'):
        logger.error('Could not parse file as an office document')
        return
    ret['office_header'] = '%d.%d' % (oparser.office_header.get('maj_ver'), oparser.office_header.get('min_ver'))

    for curr_dir in oparser.directory:
        result = {
            'md5': curr_dir.get('md5', ''),
            'size': curr_dir.get('stream_size', 0),
            'mod_time': oparser.timestamp_string(curr_dir['modify_time'])[1],
            'create_time': oparser.timestamp_string(curr_dir['create_time'])[1],
        }
        name = curr_dir['norm_name'].decode('ascii', errors='ignore')
        # TODO: why is this '' sometimes?
        if name:
            ret['directory'][name] = result
        # stream_md5 = hashlib.md5(curr_dir.get('data', b'')).hexdigest()
        # ret['added_files'].append((name, stream_md5))

    for prop_list in oparser.properties:
        for prop in prop_list['property_list']:
            prop_summary = oparser.summary_mapping.get(binascii.unhexlify(prop['clsid']), None)
            prop_name = prop_summary.get('name', 'Unknown')
            if prop_name not in ret['doc_meta']:
                ret['doc_meta'][prop_name] = {}
            for item in prop['properties']['properties']:
                result = {
                    'name': item.get('name', 'Unknown'),
                    'value': item.get('date', item['value']),
                }
                ret['doc_meta'][prop_name][result.get('name')] = result.get('value')
    return ret
