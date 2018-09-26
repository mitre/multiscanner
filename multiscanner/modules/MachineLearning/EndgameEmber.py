# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
By default, this module uses the pre-built Ember model from
https://pubdata.endgame.com/ember/ember_dataset.tar.bz2.

Documentation about training a new model can be found on the Ember GitHub page
(https://github.com/endgameinc/ember).

After training a new model, place the resulting txt file in
`multiscanner/etc` and update `config.ini` with the new filename.
"""

from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import os
from pathlib import Path

from multiscanner import CONFIG


__authors__ = "Patrick Copeland"
__license__ = "MPL 2.0"

TYPE = "MachineLearning"
NAME = "EndgameEmber"
REQUIRES = ['libmagic']
DEFAULTCONF = {
    'ENABLED': False,
    'path-to-model': os.path.join(os.path.split(CONFIG)[0], 'etc', 'ember', 'ember_model_2017.txt'),
}
LGBM_MODEL = None

try:
    import ember
    has_ember = True
except ImportError as e:
    print("ember module not installed...")
    has_ember = False

try:
    import lightgbm as lgb
except ImportError as e:
    print("lightgbm module needed for ember. Not installed...")
    has_ember = False


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not has_ember:
        return False

    if not Path(conf['path-to-model']).is_file():
        print("'{}' does not exist. Check config.ini for model location.".format(conf['path-to-model']))
        return False

    try:
        global LGBM_MODEL
        LGBM_MODEL = lgb.Booster(model_file=conf['path-to-model'])
    except lgb.LightGBMError as e:
        print("Unable to load model, {}. ({})".format(conf['path-to-model'], e))
        return False

    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []

    for fname in filelist:
        # Ensure libmagic returns results
        if REQUIRES[0] is not None:
            # only run the analytic if it is an Office document
            file_type = _get_libmagicresults(REQUIRES[0][0], fname)
            if file_type.startswith('PE32'):
                with open(fname, 'rb') as fh:
                    ember_result = ember.predict_sample(LGBM_MODEL, fh.read())
                results.append(
                    (fname, {'Prediction': ember_result})
                )

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return (results, metadata)


def _get_libmagicresults(results, fname):
    libmagicdict = dict(results)
    return libmagicdict.get(fname)
