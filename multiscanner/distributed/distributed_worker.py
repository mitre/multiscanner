#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import (absolute_import, division, print_function,
                        unicode_literals, with_statement)

import argparse
import codecs
import configparser
import multiprocessing
import os
import queue
import time
from builtins import *  # noqa: F401,F403

from future import standard_library
standard_library.install_aliases()

from multiscanner import multiscan, parse_reports
from multiscanner.common import utils
from multiscanner.storage import storage


__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

CONFIG = os.path.join(os.path.dirname(__file__), 'distconf.ini')


def multiscanner_process(work_queue, config, batch_size, wait_seconds, delete, exit_signal):
    filelist = []
    time_stamp = None
    storage_conf = utils.get_config_path(config, 'storage')
    storage_handler = storage.StorageHandler(configfile=storage_conf)
    while not exit_signal.value:
        time.sleep(1)
        try:
            filelist.append(work_queue.get_nowait())
            if not time_stamp:
                time_stamp = time.time()
            while len(filelist) < batch_size:
                filelist.append(work_queue.get_nowait())
        except queue.Empty:
            if filelist and time_stamp:
                if len(filelist) >= batch_size:
                    pass
                elif time.time() - time_stamp > wait_seconds:
                    pass
                else:
                    continue
            else:
                continue

        resultlist = multiscan(filelist, configfile=config)
        results = parse_reports(resultlist, python=True)
        if delete:
            for file_name in results:
                os.remove(file_name)

        storage_handler.store(results, wait=False)
        print('Scanned', len(results), 'files')

        filelist = []
        time_stamp = None
    storage_handler.close()


def _read_conf(file_path):
    conf = configparser.SafeConfigParser()
    conf.optionxform = str
    with codecs.open(file_path, 'r', encoding='utf-8') as fp:
        conf.readfp(fp)
    return utils.parse_config(conf)


def _main():
    args = _parse_args()
    # Pull config options
    conf = _read_conf(args.config)
    multiscanner_config = conf['worker']['multiscanner_config']

    # Start worker task
    work_queue = multiprocessing.Queue()
    exit_signal = multiprocessing.Value('b')
    exit_signal.value = False
    ms_process = multiprocessing.Process(
            target=multiscanner_process,
            args=(work_queue, multiscanner_config, args.delete, exit_signal))
    ms_process.start()

    # Start message pickup task
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        exit_signal.value = True

    print("Waiting for MultiScanner to exit...")
    ms_process.join()


def _parse_args():
    parser = argparse.ArgumentParser(description='Run MultiScanner tasks via celery')
    parser.add_argument("-c", "--config", help="The config file to use", required=False, default=CONFIG)
    parser.add_argument("--delete", action="store_true", help="Delete files once scanned")
    return parser.parse_args()


if __name__ == '__main__':
    _main()
