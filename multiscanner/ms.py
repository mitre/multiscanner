#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import (absolute_import, division, unicode_literals, with_statement)

import argparse
import codecs
import configparser
import datetime
import json
import logging
import multiprocessing
import os
import random
import re
import shutil
import six
import string
import sys
import tempfile
import threading
import time
import zipfile
from builtins import *  # noqa: F401,F403

from future import standard_library
standard_library.install_aliases()

from multiscanner.version import __version__ as MS_VERSION
from multiscanner.common.utils import (basename, convert_encoding, load_module,
                                       parse_file_list, queue2list)
from multiscanner import config as msconf
from multiscanner.config import (PY3, config_init, get_config_path,
                                 update_ms_config, update_ms_config_file,
                                 update_paths_in_config, write_missing_config)
from multiscanner.storage import storage


# The default configuration options for the main script
DEFAULTCONF = {
    "copyfilesto": False,
    "group-types": ["Antivirus"],
    "storage-config": msconf.CONFIG_FILE.replace('config.ini', 'storage.ini'),
    "api-config": msconf.CONFIG_FILE.replace('config.ini', 'api_config.ini'),
    "web-config": msconf.CONFIG_FILE.replace('config.ini', 'web_config.ini'),
}

logger = logging.getLogger(__name__)


class _Thread(threading.Thread):
    """The threading.Thread class with some more cowbell"""
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs)
        if PY3:
            self.__target = self._target
            self.__args = self._args
            self.__kwargs = self._kwargs
        # Return value from target
        self.ret = None
        # Is true when .start is called
        self.started = False
        self.name = ""
        self.starttime = 0
        self.endtime = 0

    def run(self):
        self.started = True
        self.starttime = time.time()
        try:
            if self.__target:
                self.ret = self.__target(*self.__args, **self.__kwargs)
        finally:
            self.endtime = time.time()
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self.__target, self.__args, self.__kwargs


class _GlobalModuleInterface(object):
    """
    The global module interface is a set of shared interfaces between modules.
    """
    def __init__(self, processes=None):
        self._scan_queue = multiprocessing.Queue()
        self._pool = None
        self._processes = processes
        self.write_dir = tempfile.mkdtemp(prefix='multiscan-')
        self.run_count = -1

    def _cleanup(self):
        # Remove the temp dir
        shutil.rmtree(self.write_dir, ignore_errors=True)
        if self._pool:
            self._pool.terminate()

    def scan_file(self, file_path, from_filename, module_name):
        self._scan_queue.put((file_path, from_filename, module_name))

    def _get_subscan_list(self):
        # The sleep lets the queue catch up. Sometimes results queue was detected as empty otherwise.
        time.sleep(.01)
        return queue2list(self._scan_queue)

    def apply_async(self, func, args=(), kwds={}, callback=None):
        # TODO: add option to disable async
        if not self._pool:
            self._pool = multiprocessing.Pool(processes=self._processes)
        return self._pool.apply_async(func, args=args, kwds=kwds, callback=callback)


class _ModuleInterface(object):
    """
    The module interface is a per-module interface.

    module_name - The name of the module this object will be given to
    global_interface - The global interface object that is shared among modules
    """
    def __init__(self, module_name, global_interface):
        self.global_interface = global_interface
        self.module_name = module_name
        self.write_dir = tempfile.mkdtemp(dir=self.global_interface.write_dir)
        # Put global_interface into main namespace
        self.apply_async = self.global_interface.apply_async
        self.run_count = self.global_interface.run_count

    def scan_file(self, file_path, from_filename):
        self.global_interface.scan_file(file_path, from_filename, self.module_name)

    def _cleanup(self):
        # Remove the temp dir
        shutil.rmtree(self.write_dir, ignore_errors=True)


def _run_module(modname, mod, filelist, threadDict, global_module_interface, conf=None):
    """
    Runs a module on a file list.

    Modules are loaded and check is called followed by scan.
    modname - The name of the module
    mod - The imported module
    filelist - The list of files on the host to be scanned
    threadDict - A dictionary of all threads. {modname: Thread}
    global_module_interface - The global module interface to be injected in each module
    conf - The config to be passed to the module. If None it will try to use the default conf
    """

    mod.multiscanner = _ModuleInterface(modname, global_module_interface)

    if not conf:
        try:
            conf = mod.DEFAULTCONF
        except Exception as e:
            logger.warning(e)

    required = None
    if hasattr(mod, "REQUIRES"):
        required = mod.REQUIRES
        if not isinstance(required, list):
            required = []
    # If the module has requirements
    if required:
        # Give the modules a chance to all start
        reqresults = []
        for reqmodname in required:
            if reqmodname in threadDict:
                # Wait for module to start
                while not threadDict[reqmodname].started:
                    time.sleep(5)
                # Wait for required modules to finish
                threadDict[reqmodname].join()
                # Append results to a list
                reqresults.append(threadDict[reqmodname].ret)
            else:
                # If no module of that name, append None
                reqresults.append(None)
        # Overwrite REQUIRES var
        mod.REQUIRES = reqresults
        threadDict[modname].starttime = time.time()

    if conf:
        if mod.check(conf=conf) is True:
            # If replacement path is set change the file list
            filedict = {}
            if "replacement path" in conf:
                # Copy filelist so we don't break the other modules
                filelist = filelist[:]
                for i in range(0, len(filelist)):
                    # For windows replacement paths
                    oldname = filelist[i]
                    if re.match("[a-zA-Z]:\\\\", conf["replacement path"]):
                        if conf["replacement path"].endswith("\\"):
                            filelist[i] = conf["replacement path"] + basename(filelist[i])
                        else:
                            filelist[i] = conf["replacement path"] + "\\" + basename(filelist[i])
                    # For linux replacement paths
                    else:
                        if conf["replacement path"].endswith("/"):
                            filelist[i] = conf["replacement path"] + basename(filelist[i])
                        else:
                            filelist[i] = conf["replacement path"] + "/" + basename(filelist[i])
                    filedict[filelist[i]] = oldname

                # Replace the paths on required modules if any
                if required:
                    for mresult in reqresults:
                        if mresult is None:
                            continue
                        (result, metadata) = mresult
                        for j in range(0, len(result)):
                            (filename, hit) = result[j]
                            # For windows replacement paths
                            if re.match("[a-zA-Z]:\\\\", conf["replacement path"]):
                                if conf["replacement path"].endswith("\\"):
                                    filename = conf["replacement path"] + basename(filename)
                                else:
                                    filename = conf["replacement path"] + "\\" + basename(filename)
                            # For linux replacement paths
                            else:
                                if conf["replacement path"].endswith("/"):
                                    filename = conf["replacement path"] + basename(filename)
                                else:
                                    filename = conf["replacement path"] + "/" + basename(filename)
                            result[j] = (filename, hit)
                    mod.REQUIRES = reqresults

            # Run the scan
            results = mod.scan(filelist, conf=conf)

            # If filenames were replaced, change them back
            if filedict and results:
                (result, metadata) = results
                modded = False
                for j in range(0, len(result)):
                    (filename, hit) = result[j]
                    if filename in filedict:
                        filename = filedict[filename]
                        modded = True
                        result[j] = (filename, hit)
                if modded:
                    results = (result, metadata)
            return results

        logger.debug("{} failed check(conf)".format(modname))
    else:
        if mod.check() is True:
            return mod.scan(filelist)

        logger.debug("{} failed check()".format(modname))


def _copy_to_share(filelist, filedic, sharedir):
    """
    Copies files from filelist to a share and populates the filedic. Returns a
    list of files.

    filelist - The list of file to be copied
    filedic - A dictionary used to translate files back to their original
        filenames
    sharedir - Where the files are copied to
    """
    logger.info("Copying files to share...")
    tmpfilelist = filelist[:]
    filelist = []
    for fname in tmpfilelist:
        # Build new path
        newfile = os.path.basename(fname)
        newfile = newfile.replace(' ', '_')
        newfile_path = os.path.join(sharedir, newfile)
        # If the new file exists we add in a random ID
        if os.path.exists(newfile):
            uid = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
            newfile = uid + '_' + newfile
            newfile_path = os.path.join(sharedir, newfile)
        shutil.copyfile(fname, newfile_path)
        filedic[newfile] = fname
        filelist.append(newfile_path)
    del tmpfilelist
    # Prevents file shares from making modules crash, this might not be the best but meh
    time.sleep(3)
    return filelist


def _start_module_threads(filelist, module_list, config, global_module_interface):
    """
    Starts each module on the file list in a separate thread. Returns a list of threads

    filelist - A lists of strings. The strings are files to be scanned
    module_list - A list of the names of all modules to be run
    config - The config dictionary
    global_module_interface - The global module interface to be injected in each module
    """
    logger.info("Starting modules...")
    ThreadList = []
    ThreadDict = {}
    global_module_interface.run_count += 1
    # Starts a thread for each module.
    for modname in module_list:
        # If the module is disabled we don't mess with it further to prevent spamming errors on screen
        if modname in config:
            if not config[modname].get('ENABLED', True):
                continue
        # TODO: What if the module isn't specified in the config

        try:
            moddir = msconf.MODULE_LIST[modname][1]
        except KeyError:
            logger.warning(msconf.MODULE_LIST)
            logger.warning("{} not a valid module...".format(modname))
            continue

        mod = load_module(modname, [moddir])
        if not mod:
            logger.warning("{} not a valid module...".format(modname))
            continue
        conf = None
        if modname in config:
            if '_load_default' in config or '_load_default' in config[modname]:
                try:
                    conf = mod.DEFAULTCONF
                    conf.update(config[modname])
                except Exception as e:
                    logger.warning(e)
                    conf = config[modname]
                # Remove _load_default from config
                if '_load_default' in conf:
                    del conf['_load_default']
            else:
                conf = config[modname]

        # Try and read in the default conf if one was not passed
        if not conf:
            try:
                conf = mod.DEFAULTCONF
            except Exception as e:
                logger.error(e)
        thread = _Thread(
            target=_run_module,
            args=(modname, mod, filelist, ThreadDict, global_module_interface, conf))
        thread.name = modname
        thread.setDaemon(True)
        ThreadList.append(thread)
        ThreadDict[modname] = thread

    for thread in ThreadList:
        thread.start()
    return ThreadList


def parse_reports(resultlist, groups=None, ugly=True, includeMetadata=False, python=False):
    """Turn report dictionaries into json output. Returns a string.

    resultlist - A list of the scan return values
    groups - A list of modules types that will be grouped together for the report
    ugly - If True the return json will not be formatted
    includeMetadata - If True module metadata will be included in the report
    python - If true a python dictionary is returned instead of a json string
    """
    files = {}
    metadatas = {}
    if not groups:
        groups = []
    for item in resultlist:
        if item is not None:
            (result, metadata) = item
        else:
            continue
        for (fname, hit) in result:
            if fname not in files:
                files[fname] = {}

            # Group together module results if configured
            if metadata['Type'] in groups:
                if not files[fname].get(metadata['Type'], False):
                    files[fname][metadata['Type']] = {}
                files[fname][metadata['Type']][metadata['Name']] = hit
            # Else put it in the root of the file
            else:
                files[fname][metadata['Name']] = hit
        # This is to prevent some modules from showing in metadata reports.
        if includeMetadata:
            if metadata['Name'] not in metadatas and metadata.get("Include", True):
                metadatas[metadata['Name']] = metadata

    if includeMetadata:
        finaldata = {"Files": files, "Metadata": metadatas}
    else:
        finaldata = files

    if python:
        return finaldata

    finaldata = convert_encoding(finaldata)

    if not ugly:
        return json.dumps(finaldata, sort_keys=True, indent=3, ensure_ascii=False)
    else:
        return json.dumps(finaldata, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def multiscan(Files, config=None, module_list=None):
    """
    The meat and potatoes. Returns the list of module results

    Files - A list of files and dirs to be scanned
    config - A dictionary containing the configuration options to be used.
    module_list - A list of the names of the modules to run on the files.
    """
    # Init some vars
    filelist = Files
    # A list of files in the module dir
    if module_list is None:
        module_list = [modname for modname in msconf.MODULE_LIST]
    # A dictionary used for the copyfileto parameter
    filedic = {}

    print(dict(config.items()))
    # Read in config
    if config is None:
        config = {}
    else:
        config['_load_default'] = True
    if 'main' in config:
        main_config = config['main']
    else:
        main_config = DEFAULTCONF

    # Copy files to a share if configured
    if "copyfilesto" not in main_config:
        main_config["copyfilesto"] = False
    if main_config["copyfilesto"]:
        if os.path.isdir(main_config["copyfilesto"]):
            filelist = _copy_to_share(filelist, filedic, main_config["copyfilesto"])
        else:
            raise IOError('The copyfilesto dir "' + main_config["copyfilesto"] + '" is not a valid dir')

    # Create the global module interface
    global_module_interface = _GlobalModuleInterface()

    # Start a thread for each module
    thread_list = _start_module_threads(filelist, module_list, config, global_module_interface)

    # Warn about spaces in file names
    for f in filelist:
        if ' ' in f:
            logger.warning('You are using file paths with spaces. This may result in modules not reporting correctly.')
            break

    # Wait for all threads to finish
    thread_wait_list = thread_list[:]
    verbose = logger.isEnabledFor(logging.INFO)
    i = 0
    while thread_wait_list:
        i += 1
        for thread in thread_wait_list:
            if not thread.is_alive():
                i = 0
                thread_wait_list.remove(thread)
                logger.info("Module <{0}> took {1:.5f} seconds".format(thread.name, thread.endtime - thread.starttime))
        if i == 15:
            i = 0
            if verbose:
                p = 'Waiting on'
                for thread in thread_wait_list:
                    p += ' ' + thread.name
                p += '...'
                logger.info(p)
        time.sleep(1)

    # Delete copied files
    if main_config["copyfilesto"]:
        for item in filelist:
            try:
                os.remove(item)
            except OSError as e:
                logger.debug(e)

    # Get Result list
    results = []
    for thread in thread_list:
        if thread.ret is not None:
            results.append(thread.ret)
        del thread

    # Translates file names back to the originals
    if filedic:
        # I have no idea if this is the best way to do in-place modifications
        for i in range(0, len(results)):
            (result, metadata) = results[i]
            modded = False
            for j in range(0, len(result)):
                (filename, hit) = result[j]
                base = basename(filename)
                if base in filedic:
                    filename = filedic[base]
                    modded = True
                    result[j] = (filename, hit)
            if modded:
                results[i] = (result, metadata)

    # Scan subfiles if needed
    subscan_list = global_module_interface._get_subscan_list()
    if subscan_list:
        # Translate from_filename back to original if needed
        if filedic:
            for i in range(0, len(subscan_list)):
                file_path, from_filename, module_name = subscan_list[i]
                base = basename(from_filename)
                if base in filedic:
                    from_filename = filedic[base]
                    subscan_list[i] = (file_path, from_filename, module_name)

        results.extend(_subscan(subscan_list, config, main_config, module_list, global_module_interface))

    global_module_interface._cleanup()

    return results


def _subscan(subscan_list, config, main_config, module_list, global_module_interface):
    """
    Scans files created by modules

    subscan_list - The result of _get_subscan_list() from the global module interface
    config - The configuration dictionary
    main_config - A dictionary of the configuration for main
    module_list - The list of modules
    global_module_interface - The global module interface
    """
    # The file list to be scanned
    filelist = []
    # Keeps mapping of files when they are copied to a share
    filedic = {}
    # Maps the subfile to its parent
    file_mapping = {}
    # The result list to be returned
    results = []

    # The results to map children to their parent
    parent_results = []
    # Used to map parents to their children
    subfiles_dict = {}
    # The results to map parents to their children
    subfiles_results = []
    # The results to show which module created the file
    createdby_results = []

    for file_path, from_filename, module_name in subscan_list:
        # Add each file to be scanned
        filelist.append(file_path)
        # Map file_path to the filename that will be used in the results
        new_filename = os.path.join(from_filename, basename(file_path))
        file_mapping[file_path] = (from_filename, new_filename)
        # Map the child file to its parent
        parent_results.append((new_filename, from_filename))
        # Map parent files to their children
        if from_filename not in subfiles_dict:
            subfiles_dict[from_filename] = []
        subfiles_dict[from_filename].append(new_filename)
        # Add createdby result
        createdby_results.append((new_filename, module_name))

    # Create the results for parent files
    for parent_file in subfiles_dict:
        subfiles_results.append((parent_file, subfiles_dict[parent_file]))

    # Emulate a module for so the parent child relationships are in the reports
    results.append((parent_results, {'Name': 'Parent', 'Type': 'subscan', 'Include': False}))
    results.append((subfiles_results, {'Name': 'Children', 'Type': 'subscan', 'Include': False}))
    results.append((createdby_results, {'Name': 'Created by', 'Type': 'subscan', 'Include': False}))

    del subscan_list, subfiles_dict

    # Copy files to a share if configured
    if "copyfilesto" not in main_config:
        main_config["copyfilesto"] = False
    if main_config["copyfilesto"]:
        filelist = _copy_to_share(filelist, filedic, main_config["copyfilesto"])

    # Start a thread for each module
    thread_list = _start_module_threads(filelist, module_list, config, global_module_interface)

    # Wait for all threads to finish
    thread_wait_list = thread_list[:]
    verbose = logger.isEnabledFor(logging.INFO)
    i = 0
    while thread_wait_list:
        i += 1
        for thread in thread_wait_list:
            if not thread.is_alive():
                i = 0
                thread_wait_list.remove(thread)
                logger.info("Module <{0}> took {1:.5f} seconds".format(thread.name, thread.endtime - thread.starttime))
        if i == 15:
            i = 0
            if verbose:
                p = 'Waiting on'
                for thread in thread_wait_list:
                    p += ' ' + thread.name
                p += '...'
                logger.info(p)
        time.sleep(1)

    # Delete copied files
    if main_config["copyfilesto"]:
        for item in filelist:
            os.remove(item)

    # Get Result list
    for thread in thread_list:
        if thread.ret is not None:
            results.append(thread.ret)
        del thread

    # I have no idea if this is the best way to do in-place modifications
    for i in range(0, len(results)):
        (result, metadata) = results[i]
        for j in range(0, len(result)):
            (filename, hit) = result[j]
            base = basename(filename)
            # Convert filename back if copied
            if base in filedic:
                filename = filedic[base]
                base = basename(filename)
            # Change filename to represent original file
            if filename in file_mapping:
                from_filename, new_filename = file_mapping[filename]
                result[j] = (new_filename, hit)
        results[i] = (result, metadata)

    # Scan subfiles if needed
    subscan_list = global_module_interface._get_subscan_list()
    if subscan_list:
        for i in range(0, len(subscan_list)):
            file_path, from_filename, module_name = subscan_list[i]
            base = basename(from_filename)
            # Translate from_filename back to original if needed
            if base in filedic:
                from_filename = filedic[base]
            if from_filename in file_mapping:
                null, from_filename = file_mapping[from_filename]
            subscan_list[i] = (file_path, from_filename, module_name)

        results.extend(_subscan(subscan_list, config, main_config, module_list, global_module_interface))

    return results


def _parse_args():
    """
    Parses arguments
    """
    # argparse stuff
    desc = "MultiScanner v{} - Analyze files against multiple engines"
    parser = argparse.ArgumentParser(description=desc.format(MS_VERSION))
    parser.add_argument("-c", "--config", required=False, default=None,
                        help="The config file to use")
    parser.add_argument('-j', '--json', required=False, metavar="filepath", default=None,
                        help="The json file to write")
    parser.add_argument("-m", "--metadata", action="store_true",
                        help="This will include the metadata section from the report")
    parser.add_argument('-n', '--numberper', required=False, metavar="num", default=200, type=int,
                        help="The max number of files per report")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Recursively parse folders for files to scan")
    parser.add_argument('-t', '--tag', required=False, metavar="tag", default=None,
                        help="Tags to include in the report.", action='append')
    parser.add_argument("-z", "--extractzips", action="store_true",
                        help="If any zip files are detected, extract them and scan the contents")
    parser.add_argument("-p", "--password", default="",
                        help="Password to unzip any archives listed")
    parser.add_argument("-s", "--show", action="store_true",
                        help="Print report to screen")
    parser.add_argument("-u", "--ugly", action="store_true",
                        help="If set the printed json will not have whitespace")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase output verbosity (e.g., -v, -vv, -vvv)")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                        help="Log debug messages, overrides verbose flag")
    parser.add_argument("--resume", action="store_true",
                        help="Read in the report file and continue where we left off")
    parser.add_argument('Files', nargs='+',
                        help="Files and Directories to analyze")
    return parser.parse_args()


def _get_main_modules():
    module_list = {}
    module_list['main'] = sys.modules[__name__]  # current module
    for modname, module in sorted(six.iteritems(msconf.MODULE_LIST)):
        moddir = module[1]
        mod = load_module(modname, [moddir])
        if mod:
            module_list[modname] = mod
    return module_list


def _init(args):
    # Initialize configuration file
    if args.config is None:
        args.config = msconf.CONFIG_FILE

    # Compile all the sections to go in the config
    module_list = _get_main_modules()

    if os.path.isfile(args.config):
        logger.warning('{} already exists, overwriting will destroy changes'.format(args.config))
        try:
            answer = input('Do you wish to overwrite the configuration file [y/N]:')
        except EOFError as e:
            logger.warn(e)
            answer = 'N'
        if answer == 'y':
            config = config_init(args.config, module_list)
            update_ms_config(config)  # Set global main config
            logger.info('Main configuration file initialized at {}'.format(args.config))
        else:
            logger.info('Checking for missing modules in main configuration...')
            config = msconf.MS_CONFIG  # MS_CONFIG will already have been set in main()
            write_missing_config(module_list, config, args.config)
    else:
        config = config_init(args.config, module_list)
        update_ms_config(config)  # Set global main config
        logger.info('Main configuration file initialized at {}'.format(args.config))

    # Init storage
    storage_config = get_config_path('storage')
    storage_classes = storage._get_storage_classes()
    storage_classes['main'] = sys.modules[storage.__name__]
    if os.path.isfile(storage_config):
        logger.warning('{} already exists, overwriting will destroy changes'.format(storage_config))
        try:
            answer = input('Do you wish to overwrite the configuration file [y/N]:')
        except EOFError as e:
            logger.warn(e)
            answer = 'N'
        if answer == 'y':
            config_init(storage_config, storage_classes, overwrite=True)
            logger.info('Storage configuration file initialized at {}'.format(storage_config))
        else:
            logger.info('Checking for missing modules in storage configuration...')
            config_init(storage_config, storage_classes, overwrite=False)
    else:
        config_init(storage_config, storage_classes)
        logger.info('Storage configuration file initialized at {}'.format(storage_config))

    exit(0)


def _main():
    # Get args
    args = _parse_args()

    # Send all logs to stderr and set verbose
    if args.debug or args.verbose > 1:
        log_lvl = logging.DEBUG
    elif args.verbose > 0:
        log_lvl = logging.INFO
    else:
        log_lvl = logging.WARNING

    if log_lvl == logging.DEBUG:
        logging.basicConfig(format="%(asctime)s [%(module)s] %(levelname)s: %(filename)s:%(lineno)d %(message)s",
                            stream=sys.stderr, level=log_lvl)
    else:
        logging.basicConfig(format="%(asctime)s [%(module)s] %(levelname)s: %(message)s",
                            stream=sys.stderr, level=log_lvl)

    # Check if user is trying to initialize
    if str(args.Files) == "['init']" and not os.path.isfile('init'):
        _init(args)

    # Set config or update locations
    if args.config is None:
        args.config = msconf.CONFIG_FILE
    else:
        update_ms_config_file(args.config)
        update_paths_in_config(DEFAULTCONF, msconf.CONFIG_FILE)

    if not os.path.isfile(args.config):
        module_list = _get_main_modules()
        config_init(args.config, module_list)
    else:
        # Write the default config settings for any missing modules
        module_list = _get_main_modules()
        write_missing_config(module_list, msconf.MS_CONFIG, msconf.CONFIG_FILE)

    # Make sure report is not a dir
    if args.json:
        if os.path.isdir(args.json):
            sys.exit('ERROR:', args.json, 'is a directory, a file is expected')

    # Parse the file list
    parsedlist = parse_file_list(args.Files, recursive=args.recursive)

    # Unzip zip files if asked to
    if args.extractzips:
        for fname in parsedlist:
            if zipfile.is_zipfile(fname):
                unzip_dir = os.path.join('_tmp', os.path.basename(fname))
                z = zipfile.ZipFile(fname)
                if PY3:
                    args.password = bytes(args.password, 'utf-8')
                try:
                    z.extractall(path=unzip_dir, pwd=args.password)
                    for uzfile in z.namelist():
                        parsedlist.append(os.path.join(unzip_dir, uzfile))
                except RuntimeError as e:
                    logger.error("Failed to extract {} - {}".format(fname, e))
                parsedlist.remove(fname)

    if not parsedlist:
        sys.exit("ERROR: No valid files found!")

    # Resume from report
    if args.resume:
        i = len(parsedlist)
        try:
            reportfile = codecs.open(args.json, 'r', 'utf-8')
        except Exception as e:
            logger.error(e)
            sys.exit("ERROR: Could not open report file")
        for line in reportfile:
            line = json.loads(line)
            for fname in line:
                if fname in parsedlist:
                    parsedlist.remove(fname)
        reportfile.close()
        i = i - len(parsedlist)
        logger.debug("Skipping {} files which are in the report already".format(i))

    # Do multiple runs if there are too many files
    filelists = []
    if len(parsedlist) > args.numberper:
        while len(parsedlist) > args.numberper:
            filelists.append(parsedlist[:args.numberper])
            parsedlist = parsedlist[args.numberper:]
    if parsedlist:
        filelists.append(parsedlist)

    for filelist in filelists:
        # Record start time for metadata
        starttime = str(datetime.datetime.now())

        # Run the multiscan
        results = multiscan(filelist, config=msconf.MS_CONFIG)

        # We need to read in the config for the parseReports call
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(args.config)
        config = msconf.MS_CONFIG['main']
        # Make sure we have a group-types
        if "group-types" not in config or not config["group-types"]:
            config["group-types"] = []

        # Add in script metadata
        endtime = str(datetime.datetime.now())

        try:
            username = os.getlogin()
        except Exception as e:
            # For windows compatibility
            username = os.getenv('USERNAME')
            logger.debug(e)

        # Add metadata to the scan
        results.append((
            [],
            {
                "Name": "MultiScanner",
                "Start Time": starttime,
                "End Time": endtime,
                # "Command Line":list2cmdline(sys.argv),
                "Run by": username
            }
        ))

        # Add tags if present
        if args.tag:
            tag_results = []
            for filename in filelist:
                tag_results.append((filename, args.tag))
            results.append((
                tag_results,
                {
                    "Name": "tags",
                    "Type": "Metadata"
                }
            ))

        if args.show or not sys.stdout.isatty():
            # TODO: Make this output something readable
            # Parse Results
            report = parse_reports(results, groups=config["group-types"], ugly=args.ugly, includeMetadata=args.metadata)

            # Print report
            try:
                logger.info(convert_encoding(report, encoding='ascii', errors='replace'))
            except Exception as e:
                logger.error('Can\'t print report - {}'.format(e))

        report = parse_reports(results, groups=config["group-types"], includeMetadata=args.metadata, python=True)

        update_conf = None
        if args.json:
            update_conf = {'File': {'path': args.json}}
            if args.json.endswith('.gz') or args.json.endswith('.gzip'):
                update_conf['File']['gzip'] = True

        if 'storage-config' not in config:
            config["storage-config"] = None
        storage_handle = storage.StorageHandler(configfile=config["storage-config"], config=update_conf)
        storage_handle.store(report)
        storage_handle.close()

    # Cleanup zip extracted files
    if args.extractzips:
        shutil.rmtree('_tmp')


if __name__ == "__main__":
    _main()
