# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import mmap
try:
    import floss
    from floss.identification_manager import identify_decoding_functions
    from floss.main import decode_strings, get_all_plugins, sanitize_string_for_printing
    from floss.stackstrings import extract_stackstrings
    from floss.strings import extract_ascii_strings, extract_unicode_strings
    from floss.utils import get_vivisect_meta_info
    import viv_utils
except ImportError:
    print("floss module is not installed...")
    floss = False

__author__ = "Emmanuelle Vargas-Gonzalez"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "floss"
DEFAULTCONF = {
    "ENABLED": False,
    "min-str-length": 4
}


def check(conf=DEFAULTCONF):
    if not conf["ENABLED"]:
        return False
    if not floss:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []
    selected_plugins = get_all_plugins()

    for fname in filelist:
        with open(fname, "rb") as f:
            ret = {}
            b = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            vw = viv_utils.getWorkspace(fname, should_save=False)

            extracted_ascii = list(s.s for s in extract_ascii_strings(b, conf["min-str-length"]))

            if extracted_ascii:
                ret["static_ascii_strings"] = extracted_ascii

            extracted_unicode = list(s.s for s in extract_unicode_strings(b, conf["min-str-length"]))

            if extracted_unicode:
                ret["static_utf16_strings"] = extracted_unicode

            decoding_functions_candidates = identify_decoding_functions(vw, selected_plugins, vw.getFunctions())
            decoded_strings = decode_strings(vw, decoding_functions_candidates, conf["min-str-length"])
            decoded_strings = list(sanitize_string_for_printing(s.s) for s in decoded_strings)

            if decoded_strings:
                ret["decoded_strings"] = decoded_strings

            extracted_stackstrings = list(s.s for s in extract_stackstrings(vw, vw.getFunctions(), conf["min-str-length"], False))

            if extracted_stackstrings:
                ret["stack_strings"] = extracted_stackstrings

            extracted_vivisect_meta = get_vivisect_meta_info(vw, None)

            if extracted_vivisect_meta:
                extracted_meta = {}
                for k, v in extracted_vivisect_meta:
                    if not v:
                        extracted_meta[k] = "N\A"
                    else:
                        extracted_meta[k] = v
                extracted_vivisect_meta = extracted_meta
                ret["vivisect_meta_info"] = extracted_vivisect_meta

            if ret:
                results.append((fname, ret))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)
