#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import (absolute_import, division, print_function,
                        unicode_literals, with_statement)

import argparse
import multiprocessing
import os
import queue
import threading
import time
from builtins import *  # noqa: F401,F403

from future import standard_library
standard_library.install_aliases()

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from multiscanner import CONFIG as MS_CONFIG
from multiscanner import multiscan, parse_reports
from multiscanner.common import utils
from multiscanner.storage import storage


class DirWatcher(FileSystemEventHandler):
    def __init__(self, work_queue):
        super(DirWatcher, self).__init__()
        self.work_queue = work_queue

    def on_moved(self, event):
        if not event.is_directory:
            print("File moved:", event.dest_path)
            self.startwatch(event.dest_path)

    def on_created(self, event):
        if not event.is_directory:
            print("File created:", event.src_path)
            self.startwatch(event.src_path)

    def startwatch(self, file_path):
        thread = threading.Thread(target=self.watch, args=(file_path,))
        thread.start()

    def watch(self, file_path):
        # TODO: Maybe this should be replaced with something that flags on a file being closed
        while True:
            # Wait for file to stop being written to for 3 seconds
            try:
                file_stat = os.stat(file_path)
                time.sleep(3)
                while os.stat(file_path) != file_stat or int(file_stat.st_size) <= 0:
                    file_stat = os.stat(file_path)
                    time.sleep(3)
                print("File Finished:", file_path)
            except Exception as e:
                print("ERROR:", e)
                return
            # Try to open the file for writing
            try:
                open(file_path, 'a+').close()
                # File is considered done if we can open it for writing
                break
            except IOError:
                pass
        self.work_queue.put(file_path)


def start_observer(directory, work_queue, recursive=False):
    event_handler = DirWatcher(work_queue)
    observer = Observer()
    observer.schedule(event_handler, path=directory, recursive=recursive)
    observer.start()
    return observer


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


def _main():
    args = _parse_args()
    work_queue = multiprocessing.Queue()
    exit_signal = multiprocessing.Value('b')
    exit_signal.value = False
    observer = start_observer(args.Directory, work_queue, args.recursive)
    ms_process = multiprocessing.Process(
        target=multiscanner_process,
        args=(work_queue, args.config, args.batch, args.seconds, args.delete, exit_signal))
    ms_process.start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        exit_signal.value = True
        observer.stop()
    observer.join()
    print("Waiting for MultiScanner to exit...")
    ms_process.join()


def _parse_args():
    parser = argparse.ArgumentParser(description='Monitor a directory and submit new files to MultiScanner')
    parser.add_argument("-c", "--config", help="The config file to use", required=False,
                        default=MS_CONFIG)
    parser.add_argument("-s", "--seconds", help="The number of seconds to wait for additional files",
                        required=False, default=120, type=int)
    parser.add_argument("-b", "--batch", help="The max number of files per batch", required=False,
                        default=100, type=int)
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively watch for files to scan")
    parser.add_argument("--delete", action="store_true", help="Delete files once scanned")
    parser.add_argument('Directory', help="Directory to monitor for files")
    return parser.parse_args()


if __name__ == '__main__':
    _main()
