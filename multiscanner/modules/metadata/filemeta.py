# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, unicode_literals
import logging
import math

from collections import Counter
from hashlib import md5, sha1, sha256, sha512
from zlib import crc32

logger = logging.getLogger(__name__)

try:
    import magic
except ImportError:
    logger.warning("python-magic module not installed...")
    magic = False

__author__ = "Patrick Copeland"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "filemeta"


def check():
    return True


def scan(filelist):
    results = []

    for fname in filelist:
        filemeta_d = {}

        with open(fname, 'rb') as fh:
            buf = fh.read()

        # hashes
        filemeta_d['md5'] = hashfile(buf, md5())
        filemeta_d['sha1'] = hashfile(buf, sha1())
        filemeta_d['sha256'] = hashfile(buf, sha256())
        filemeta_d['sha512'] = hashfile(buf, sha512())
        filemeta_d['crc32'] = hex(crc32(buf) & 0xffffffff)  # not chunking here

        # size
        filemeta_d['filesize'] = len(buf)

        # entropy
        filemeta_d['entropy'] = calculate_entropy(buf)

        # magic
        if magic:
            filemeta_d.update(get_magic(buf))

        results.append((fname, filemeta_d))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)


def hashfile(buf, hasher, blocksize=65536):
    """
    Hashes a file in chunks and returns the hash algorithms digest.

    fname - The file to be hashed
    hasher - The hasher from hashlib. E.g. hashlib.md5()
    blocksize - The size of each block to read in from the file
    """
    index = 1
    block = buf[:blocksize]
    while len(block) > 0:
        hasher.update(block)
        block = buf[blocksize * index:blocksize * (index + 1)]
        index += 1

    return hasher.hexdigest()


def calculate_entropy(buf):
    chars, lns = Counter(buf), float(len(buf))
    entropy = -sum(count / lns * math.log(count / lns, 2) for count in chars.values())

    return entropy


def get_magic(buf):
    return {
        'filetype': magic.from_buffer(buf),
        'mimetype': magic.from_buffer(buf, mime=True)
    }
