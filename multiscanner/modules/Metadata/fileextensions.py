# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import mimetypes

__author__ = 'Austin West'
__license__ = 'MPL 2.0'

TYPE = 'Metadata'
NAME = 'fileextensions'
REQUIRES = ['libmagic', 'Tika', 'TrID', 'vtsearch']
DEFAULTCONF = {
    'ENABLED': True
}

EXTENSION_BLACKLIST = [
    '.virus',
    '.exe_',
    '.ex_',
    '.partial',
]


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    else:
        return True


def scan(filelist, conf=DEFAULTCONF):
    # Init the mimetypes library
    mimetypes.init()
    results = []

    for fname in filelist:
        # Check if any of the required modules are empty before
        # attempting to parse the results
        if REQUIRES[0] is not None:
            libmagicr = _get_libmagicresults(REQUIRES[0][0], fname)
        else:
            libmagicr = []
        if REQUIRES[1] is not None:
            tikar = _get_tikaresults(REQUIRES[1][0], fname)
        else:
            tikar = []
        if REQUIRES[2] is not None:
            tridr = _get_tridresults(REQUIRES[2][0], fname)
        else:
            tridr = []
        if REQUIRES[3] is not None:
            vtr = _get_vtresults(REQUIRES[3][0], fname)
        else:
            vtr = []

        result = {}
        result['libmagic'] = libmagicr
        result['tika'] = tikar
        result['trid'] = tridr
        result['vt'] = vtr
        results.append((fname, result))

    metadata = {}
    metadata['Name'] = NAME
    metadata['Type'] = TYPE
    metadata['Include'] = False
    return (results, metadata)


def _get_libmagicresults(results, fname):
    libmagicdict = dict(results)
    return _convert_libmagic_to_extension(
        libmagicdict.get(fname)
    )


def _get_tikaresults(results, fname):
    # Tika mime type is under Content-Type key.
    # Take the content type and make a guess of the
    # mimetype using python's built in mimetypes lib.
    tikadict = dict(results)
    try:
        content_types = tikadict.get(fname, {}).get('Content-Type')

        if not isinstance(content_types, list):
            content_types = [content_types]

        tika_extensions = []
        for ctype in content_types:
            tika_extensions += mimetypes.guess_all_extensions(ctype)

        return list(set(tika_extensions))

    except AttributeError:
        return []


def _get_tridresults(results, fname):
    # Loop through the TrID results and
    # pull out all the possible extensions. Then,
    # make them all lowercase and de-duplicate them.
    triddict = dict(results)
    result = []
    for tridresult in triddict.get(fname):
        result.append(tridresult[2].lower())
    # make trid results unique
    result = list(set(result))
    return result


def _get_vtresults(results, fname):
    # Loop through all the submission names in the VT result
    # If there is a '.' in the submision name, pull anything after
    # the last '.' as the file extension
    vtdict = dict(results)
    result = []
    for submission_name in vtdict.get(fname, {}).get('submission_names', []):
        if '.' in submission_name:
            extension = '.{}'.format(submission_name.split('.')[-1])
            if extension not in EXTENSION_BLACKLIST:
                result.append(extension)
    result = list(set(result))
    return result


def _convert_libmagic_to_extension(libmagicresult):
    # Do some detction on the libmmagic results and return
    # a best guess of extension

    if 'Microsoft Word 2007+' in libmagicresult:
        return ['.docx']
    elif 'Microsoft Word' in libmagicresult:
        return ['.doc']
    elif 'Microsoft PowerPoint 2007+' in libmagicresult:
        return ['.pptx']
    elif 'Microsoft PowerPoint' in libmagicresult:
        return ['.ppt']
    elif 'Rich Text Format data' in libmagicresult:
        return ['.rtf']
    elif 'Microsoft Excel 2007+' in libmagicresult:
        return ['.xlsx']
    elif 'Microsoft Excel' in libmagicresult:
        return ['.xls']
    elif 'GIF image data' in libmagicresult:
        return ['.gif']
    elif 'JPEG image data' in libmagicresult:
        return ['.jpg']
    elif 'PDF document' in libmagicresult:
        return ['.pdf']
    elif 'PNG image data' in libmagicresult:
        return ['.png']
    elif 'PE32 executable (GUI)' in libmagicresult:
        return ['.exe']
    elif 'PE32+ executable (GUI)' in libmagicresult:
        return ['.exe']
    elif 'PE32 executable (DLL)' in libmagicresult:
        return ['.dll']
    elif 'PE32+ executable (DLL)' in libmagicresult:
        return ['.dll']
    elif 'XML' in libmagicresult:
        return ['.xml']
    elif 'ms-windows metafont .wmf' in libmagicresult:
        return ['.wmf']
    elif 'Windows Enhanced Metafile (EMF) image data' in libmagicresult:
        return ['.mf']
    elif 'TIFF image data' in libmagicresult:
        return ['.tif']
    elif 'PC bitmap' in libmagicresult:
        return ['.bmp']
    elif '7-zip archive data' in libmagicresult:
        return ['.7z']
    elif 'bzip2 compressed data' in libmagicresult:
        return ['.bz2']
    elif 'gzip compressed data' in libmagicresult:
        return ['.gz']
    elif 'POSIX tar archive' in libmagicresult:
        return ['.tar']
    elif 'RAR archive data' in libmagicresult:
        return ['.rar']
    elif 'Java archive data' in libmagicresult:
        return ['.jar']
    elif 'MS-DOS executable' in libmagicresult:
        return ['.exe']
    elif 'DOS executable' in libmagicresult:
        return ['.com']
    elif 'COM executable' in libmagicresult:
        return ['.com']
    elif 'UTF-8 Unicode text' in libmagicresult:
        return ['.txt']
    elif 'UTF-8 Unicode (with BOM) text' in libmagicresult:
        return ['.txt']
    elif 'ISO-8859 text' in libmagicresult:
        return ['.txt']
    elif 'ASCII text' in libmagicresult:
        return ['.txt']
    elif 'MS Windows shortcut' in libmagicresult:
        return ['.lnk']
    elif 'Microsoft Cabinet archive data' in libmagicresult:
        return ['.cab']
    elif 'PHP script' in libmagicresult:
        return ['.ph']
    elif 'empty' in libmagicresult:
        return ['.empty']
    elif 'HTML document' in libmagicresult:
        return ['.html']
    else:
        return []
