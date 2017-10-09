# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import subprocess

__author__ = "Emmanuelle Vargas-Gonzalez"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "floss"
DEFAULTCONF = {
    "ENABLED": False,
    "path": "C:\\floss64.exe",
    "cmdline": ["--show-metainfo"]
}


def check(conf=DEFAULTCONF):
    if not conf["ENABLED"]:
        return False
    if os.path.isfile(conf["path"]):
        return True
    else:
        return False


def scan(filelist, conf=DEFAULTCONF):
    results = []

    for fname in filelist:
        ret = {}
        cmd = _build_command(conf, fname)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        for f in p.stdout:
            if "FLOSS static ASCII strings" in f:
                ret["static_ascii_strings"] = []
                f = next(p.stdout, "")
                while f != "":
                    ret["static_ascii_strings"].append(f)
                    f = next(p.stdout, "")
                    f = f.strip()
            elif "FLOSS static UTF-16 strings" in f:
                ret["static_utf16_strings"] = []
                f = next(p.stdout, "")
                while f != "":
                    ret["static_utf16_strings"].append(f)
                    f = next(p.stdout, "")
                    f = f.strip()
            elif "FLOSS decoded" in f:
                ret["decoded_strings"] = []
                f = next(p.stdout, "")
                while f != "":
                    ret["decoded_strings"].append(f)
                    f = next(p.stdout, "")
                    f = f.strip()
            elif "stackstrings" in f:
                ret["stack_strings"] = []
                f = next(p.stdout, "")
                while f != "":
                    ret["stack_strings"].append(f)
                    f = next(p.stdout, "")
                    f = f.strip()
            elif "Vivisect workspace analysis information" in f:
                ret["vivisect_meta_info"] = []
                f = next(p.stdout, "")
                while f != "":
                    ret["vivisect_meta_info"].append(f)
                    f = next(p.stdout, "")
                    f = f.strip()

        if ret:
            results.append((fname, ret))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)


def _build_command(conf, fname):
    cmd = [conf["path"], fname]
    cmd.extend(conf["cmdline"])

    return cmd
