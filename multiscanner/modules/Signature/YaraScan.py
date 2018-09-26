# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import os
import time

from multiscanner.config import CONFIG
from multiscanner.common.utils import parseDir


__authors__ = "Nick Beede, Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Signature"
NAME = "Yara"
DEFAULTCONF = {
    "ruledir": os.path.join(os.path.split(CONFIG)[0], "etc", "yarasigs"),
    "fileextensions": [".yar", ".yara", ".sig"],
    "ignore-tags": ["TLPRED"],
    "includes": False,
    "ENABLED": True
}

try:
    import yara
except ImportError:
    print("yara-python module not installed...")
    yara = False


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not yara:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    ruleDir = conf["ruledir"]
    extlist = conf["fileextensions"]
    includes = 'includes' in conf and conf['includes']

    ruleset = {}
    rules = parseDir(ruleDir, recursive=True)
    for r in rules:
        for ext in extlist:
            if r.endswith(ext):
                full_path = os.path.abspath(os.path.join(ruleDir, r))
                ruleset[full_path] = full_path
                break

    # Ran into a weird issue with file locking, this fixes it
    goodtogo = False
    i = 0
    yararules = None
    while not goodtogo:
        try:
            yararules = yara.compile(filepaths=ruleset, includes=includes)
            goodtogo = True
        except yara.SyntaxError as e:
            bad_file = os.path.abspath(str(e).split('(')[0])
            if bad_file in ruleset:
                del ruleset[bad_file]
                print('WARNING: Yara', e)
            else:
                print('ERROR Yara: Invalid rule in', bad_file, 'but we are unable to remove it from our list. Aborting')
                print(e)
                return None

    matches = []
    for m in filelist:
        # Ran into a weird issue with file locking, this fixes it
        goodtogo = False
        i = 0
        while not goodtogo and i < 5:
            try:
                f = open(m, 'rb')
                goodtogo = True
            except Exception as e:
                print('yara:', e)
                time.sleep(3)
                i += 1
        try:
            hit = yararules.match(data=f.read())
        except Exception as e:
            # TODO: log exception
            continue
        finally:
            f.close()
        if hit:
            hdict = {}
            for h in hit:
                if not set(h.tags).intersection(set(conf["ignore-tags"])):
                    hit_dict = {
                        'meta': h.meta,
                        'namespace': h.namespace,
                        'rule': h.rule,
                        'tags': h.tags,
                    }
                    try:
                        h_key = '{}:{}'.format(hit_dict['namespace'].split('/')[-1], hit_dict['rule'])
                    except IndexError:
                        h_key = '{}'.format(hit_dict['rule'])
                    hdict[h_key] = hit_dict
            matches.append((m, hdict))

    metadata = {}
    rulelist = list(ruleset)
    rulelist.sort()
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Rules"] = rulelist
    return (matches, metadata)
