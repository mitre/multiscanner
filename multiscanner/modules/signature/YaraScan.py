# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import binascii
import logging
import os
import time

import multiscanner as ms
from multiscanner.common.utils import parse_dir


__authors__ = "Nick Beede, Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Signature"
NAME = "Yara"
DEFAULTCONF = {
    "ruledir": os.path.join(os.path.split(ms.config.CONFIG_FILE)[0], "etc", "yarasigs"),
    "fileextensions": [".yar", ".yara", ".sig"],
    "ignore-tags": ["TLPRED"],
    "string-threshold": 30,
    "includes": False,
    "ENABLED": True
}

logger = logging.getLogger(__name__)

try:
    import yara
except ImportError:
    logger.error("yara-python module not installed...")
    yara = False


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not yara:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    ruleDir = conf['ruledir']
    extlist = conf['fileextensions']
    string_threshold = conf['string-threshold']
    includes = 'includes' in conf and conf['includes']

    ruleset = {}
    try:
        rules = parse_dir(ruleDir, recursive=True)
    except (OSError, IOError) as e:
        logger.error('Cannot read files: {}'.format(e.filename))
        return None
    for r in rules:
        for ext in extlist:
            if r.endswith(ext):
                full_path = os.path.abspath(os.path.join(ruleDir, r))
                ruleset[full_path] = full_path
                break

    # Ran into a weird issue with file locking, this fixes it
    goodtogo = False
    yararules = None
    while not goodtogo:
        try:
            yararules = yara.compile(filepaths=ruleset, includes=includes)
            goodtogo = True
        except yara.SyntaxError as e:
            bad_file = os.path.abspath(str(e).split('(')[0])
            if bad_file in ruleset:
                del ruleset[bad_file]
                logger.warning(e)
            else:
                logger.error('Invalid Yara rule in {} but we are unable to '
                             'remove it from our list. Aborting'.format(bad_file))
                logger.error(e)
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
                logger.error(e)
                time.sleep(3)
                i += 1
        try:
            hits = yararules.match(data=f.read())
        except Exception as e:
            logger.error(e)
            continue
        finally:
            f.close()
        if hits:
            hdict = {}
            for h in hits:
                if not set(h.tags).intersection(set(conf["ignore-tags"])):
                    hit_dict = {
                        'namespace': h.namespace,
                        'rule': h.rule
                    }
                    try:
                        h_key = '{}:{}'.format(hit_dict['namespace'].split('/')[-1], hit_dict['rule'])
                    except IndexError:
                        h_key = '{}'.format(hit_dict['rule'])

                    if h_key not in hdict:
                        if h.tags:
                            hit_dict['tags'] = h.tags
                        if h.meta:
                            hit_dict['meta'] = h.meta

                        if len(h.strings) > string_threshold:
                            msg = 'String matches from YARA rule {} were not included because they surpass ' \
                                  'the threshold of {}. Found {}.'
                            logger.warning(msg.format(h_key, string_threshold, len(h.strings)))

                        else:
                            # Largely based on:
                            # https://github.com/crits/crits_services/blob/master/yara_service/__init__.py#L261
                            strings_dict = {}

                            for s in h.strings:
                                s_name = s[1]
                                s_offset = s[0]

                                try:
                                    s_data = s[2].decode('ascii')
                                except UnicodeError:
                                    s_data = 'Hex: {}'.format(binascii.hexlify(s[2]).decode('ascii'))

                                s_key = '{0}-{1}'.format(s_name, s_data)

                                if s_key in strings_dict:
                                    strings_dict[s_key]['offset'].append(s_offset)
                                else:
                                    strings_dict[s_key] = {
                                        'offset': [s_offset],
                                        'name': s_name,
                                        'data': s_data,
                                    }

                            if strings_dict:
                                hit_dict['strings'] = [x for x in strings_dict.values()]
                        hdict[h_key] = hit_dict

            matches.append((m, [x for x in hdict.values()]))

    metadata = {}
    rulelist = list(ruleset)
    rulelist.sort()
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Rules"] = rulelist
    return (matches, metadata)
