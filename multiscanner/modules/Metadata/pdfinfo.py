# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import hashlib
import math
import re

from multiscanner.config import PY3
from multiscanner.ext import pdfparser

__author__ = "Drew Bonasera"
__credits__ = ["Wesley Shields", "Mike Goffin"]
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "pdfinfo"
REQUIRES = ["libmagic"]
DEFAULTCONF = {
    'ENABLED': True,
    'fast': False
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if None in REQUIRES:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []
    libmagicresults, libmagicmeta = REQUIRES[0]
    for fname, libmagicresult in libmagicresults:
        if libmagicresult.startswith('PDF document'):
            ret = None
            try:
                handle = open(fname, 'rb')
                ret = run(fname, handle.read(), fast=conf['fast'])
            except Exception as e:
                print('pdfinfo:', e)
            finally:
                handle.close()
            if ret:
                results.append((fname, ret))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)

# This section is an adaption from the CRITS pdfinfo service
# https://github.com/MITRECND/crits_services/blob/master/pdfinfo_service/__init__.py


def H(data):
    if not data:
        return 0
    data = data.decode('utf-8', 'replace')
    entropy = 0
    for x in range(256):
        p_x = float(data.count(chr(x))) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy


def _get_pdf_version(data):
    header_ver = re.compile(r'%PDF-([A-Za-z0-9\.]{1,3})[\r\n]', re.M)
    matches = header_ver.match(data.decode('UTF-8', 'replace'))
    if matches:
        return matches.group(1)
    else:
        return "0.0"


def run(fname, data, fast=False):
    ret = {}
    ret['objects'] = {}
    ret['stats'] = {}
    # data = obj.filedata.read()
    object_summary = {
        'XRef': 0,
        'Catalog': 0,
        'ObjStm': 0,
        'Page': 0,
        'Metadata': 0,
        'XObject': 0,
        'Sig': 0,
        'Pages': 0,
        'FontDescriptor': 0,
        'Font': 0,
        'EmbeddedFile': 0,
        'StructTreeRoot': 0,
        'Mask': 0,
        'Group': 0,
        'Outlines': 0,
        'Action': 0,
        'Annot': 0,
        'Other_objects': 0,
        'Encoding': 0,
        'ExtGState': 0,
        'Pattern': 0,
        '3D': 0,
        'Total': 0,
        'Version': '',
    }
    object_summary["Version"] = _get_pdf_version(data[:1024])
    oPDFParser = pdfparser.cPDFParser(fname)
    done = True
    # self._debug("Parsing document")
    while done is True:
        try:
            pdf_object = oPDFParser.GetObject()
        except Exception as e:
            pdf_object = None
        if pdf_object is not None:
            if pdf_object.type in [pdfparser.PDF_ELEMENT_INDIRECT_OBJECT]:
                rawContent = pdfparser.FormatOutput(pdf_object.content, True)
                if PY3:
                    rawContent = rawContent.encode('utf-8', 'replace')
                object_type = pdf_object.GetType()
                if not fast:
                    section_md5_digest = hashlib.md5(rawContent).hexdigest()
                    section_entropy = H(rawContent)
                    result = {
                            "obj_id": pdf_object.id,
                            "obj_version": pdf_object.version,
                            "size": len(rawContent),
                            "md5": section_md5_digest,
                            "type": object_type,
                            "entropy": section_entropy,
                    }
                else:
                    result = {
                            "obj_id": pdf_object.id,
                            "obj_version": pdf_object.version,
                            "size": len(rawContent),
                            "type": object_type,
                    }

                if object_type[1:] in object_summary:
                    object_summary[object_type[1:]] += 1
                else:
                    object_summary["Other_objects"] += 1
                object_summary["Total"] += 1
                # self._add_result('pdf_object', pdf_object.id, result)
                ret['objects'][pdf_object.id] = result
        else:
            done = False
    for item in object_summary.items():
        # item_str = "{0}: {1}".format(item[0], item[1])
        # self._add_result('stats', item_str, {'type': item[0], 'count': item[1]})
        ret['stats'][item[0]] = item[1]
    return ret
