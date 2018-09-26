# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import time
import shutil

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Detonation"
NAME = "FireEye"
DEFAULTCONF = {
    "fireeye images": ["win7-sp1", "win7x64-sp1", "winxp-sp2", "winxp-sp3"],
    "ENABLED": False,
    "good path": "good",
    "base path": "/mnt/fireeyeshare/",
    "bad path": "bad",
    "src path": "src"
}


def check(conf=DEFAULTCONF):
    return conf["ENABLED"]


def scan(filelist, conf=DEFAULTCONF):
    base = conf["base path"]
    FEGood = conf["good path"]
    FEBad = conf["bad path"]
    FESrc = conf["src path"]
    FireEyeImages = conf["fireeye images"]
    results = {}
    resultlist = []
    waitlist = []

    # Checks if the img dir exist in list, if not remove
    for imgPath in FireEyeImages[:]:
        if not (os.path.isdir(os.path.join(base, imgPath))):
            print("WARNING: Fireeye path not found -", (os.path.join(base, imgPath)))
            FireEyeImages.remove(imgPath)

    timestamp = str(time.time()).replace('.', '-')
    for fname in filelist:
        filename = timestamp + "-" + os.path.basename(fname)
        for img in FireEyeImages:
            shutil.copyfile(fname, os.path.join(base, img, FESrc, filename))
            waitlist.append((filename, img, fname))
        results[fname] = []

    while waitlist:
        for filename, img, fname in waitlist[:]:
            if os.path.isfile(os.path.join(base, img, FEGood, filename)):
                os.remove(os.path.join(base, img, FEGood, filename))
            elif os.path.isfile(os.path.join(base, img, FEBad, filename)):
                results[fname].append(img)
                os.remove(os.path.join(base, img, FEBad, filename))
            else:
                continue
            waitlist.remove((filename, img, fname))
        time.sleep(20)

    for key, result in results.items():
        if results:
            result.sort()
            resultlist.append((key, result))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return (resultlist, metadata)
