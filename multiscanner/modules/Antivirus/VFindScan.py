'''
Antivirus module for the CyberSoft VFind anti-malware scanner;
a part of the VFind Security Toolkit (VSTK).

More information about these tools can be found at:
    https://www.cybersoft.com/products/vstk/
    https://www.cybersoft.com/support/training/

Configuration options:
    `vstk_home' - path to your VSTK installation directory
    `uad_cmdline' - additional command line options for UAD (filetype identification + metadata)
    `vfind_cmdline' - additional command line options for VFind

Additional notes:
    The UAD tool is run a second time here instead of using data directly from the UADScan metadata
    module. This is done for simplicity and should not adversely effect performance. Note that UAD
    does not perform file expansion again when used in this module.
'''

import os
import re
import subprocess

__author__ = "Alec Hussey"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "VFind"

DEFAULTCONF = {
    "ENABLED": False,
    "vstk_home": "/opt/vstk",
    "uad_cmdline": [],
    "vfind_cmdline": []
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not os.path.isdir(conf['vstk_home']):
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    uad_command = [os.path.join(conf['vstk_home'], "bin/uad"), "-n", "-ssw"] + conf['uad_cmdline'] + filelist
    vfind_command = [os.path.join(conf['vstk_home'], "bin/vfind"), "-ssr"] + conf['vfind_cmdline']

    try:
        uad = subprocess.Popen(uad_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        vfind = subprocess.Popen(vfind_command, stdin=uad.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = vfind.communicate(timeout=21600)[0].decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as error:
        return None

    results = re.findall("^##==>>>> VIRUS POSSIBLE IN FILE: \"(.+)\"\n##==>>>> VIRUS ID: (\w+ .+)",
                         output,
                         re.MULTILINE)

    vfind_version = ""
    try:
        vfind_version = re.search("^##==> VFind Version: (\d+), Release: (\d+), Patchlevel: (\d+) .+", output)
        vfind_version = "{}.{}.{}".format(
            vfind_version.group(1),
            vfind_version.group(2),
            vfind_version.group(3)
        )
    except Exception as e:
        # TODO: log exception
        pass

    with open(os.path.join(conf['vstk_home'], "data/vfind/VERSION"), "r") as vdl_version_file:
        vdl_version = vdl_version_file.read().strip()

    metadata = {
        "Type": TYPE,
        "Name": NAME,
        "Program version": vfind_version,
        "Definition version": vdl_version
    }

    return (results, metadata)
