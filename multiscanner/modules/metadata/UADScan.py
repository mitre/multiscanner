'''
Metadata module for the CyberSoft Universal Atomic Disintegrator (UAD) tool;
a part of the VFind Security Toolkit (VSTK). This module performs filetype
identification and expansion.

More information about these tools can be found at:
    https://www.cybersoft.com/products/vstk/
    https://www.cybersoft.com/support/training/
'''

import os
import re
import subprocess

__author__ = "Alec Hussey"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "UAD"

DEFAULTCONF = {
    "ENABLED": False,
    "vstk_home": "/opt/vstk",
    "cmdline": []
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not os.path.isdir(conf['vstk_home']):
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []
    # TODO: is this how we want to expose these multiscanner interface?
    command = [os.path.join(conf['vstk_home'], "bin/uad"), "-k", "-t", multiscanner.write_dir]  # noqa F821

    for input_file in filelist:
        command2 = command[:]
        command2.append(input_file)

        try:
            output = subprocess.check_output(command2)
            output = output.decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as error:
            return None

        # find and submit expanded files for scanning
        components = re.findall(r"^(\d+): Tmpfile: (.+)$", output, re.MULTILINE)

        for item in components:
            # skip base level items to avoid rescanning files already expanded
            # this happens when passing in a component to a new instance of UAD
            if int(item[0]) == 0:
                continue

            # TODO: is this how we want to expose the multiscanner interface?
            # TODO: is there a max recursion depth?
            multiscanner.scan_file(item[1], input_file) # noqa F821

        results += re.findall(r"^0: Name: (.+)\n^\d+: Type: (.+)$", output, re.MULTILINE)

    metadata = {
        "Type": TYPE,
        "Name": NAME
    }

    return (results, metadata)
