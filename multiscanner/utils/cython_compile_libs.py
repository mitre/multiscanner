#!/bin/env python
from __future__ import (absolute_import, division, unicode_literals, with_statement)

import os
import logging
import shutil

from pyximport.pyxbuild import pyx_to_dll

from multiscanner.common import utils

WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBS = os.path.join(WD, 'libs')

logger = logging.get_logger(__name__)


def main():
    filelist = utils.parseFileList([LIBS], recursive=True)
    try:
        import pefile
        filepath = pefile.__file__[:-1]
        filelist.append(filepath)
    except ImportError:
        logger.error('pefile not installed...')
    for filename in filelist:
        if filename.endswith('.py'):
            filename = str(filename)
            try:
                pyx_to_dll(filename, inplace=True)
                logger.info('{} successful!'.format(filename))
            except Exception as e:
                logger.error('{} failed'.format(filename))
                logger.exception(e)
            try:
                os.remove(filename[:-2] + 'c')
            except Exception as e:
                logger.exception(e)

    # Cleanup build dirs
    walk = os.walk(LIBS)
    for path in walk:
        path = path[0]
        if os.path.basename(path) == '_pyxbld' and os.path.isdir(path):
            shutil.rmtree(path)


if __name__ == '__main__':
    main()
