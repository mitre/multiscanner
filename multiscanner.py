#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
from builtins import *
from future import standard_library
standard_library.install_aliases()
import sys
import os
import json
import re
import shutil
import time
import datetime
import random
import string
import threading
import configparser
import codecs
import multiprocessing
import tempfile
import storage
import common

PY3 = False
if sys.version_info < (2, 7) or sys.version_info > (4,):
    print("WARNING: You're running an untested version of python")
elif sys.version_info > (3,):
    PY3 = True

if PY3:
    raw_input = input

# Gets the directory that this file is in
MS_WD = os.path.dirname(os.path.abspath(__file__))
# Adds the libs directory to the path
if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.append(os.path.join(MS_WD, 'libs'))

# The default config file
CONFIG = os.path.join(MS_WD, "config.ini")

# The directory where the modules are kept
MODULEDIR = os.path.join(MS_WD, "modules")

# The default configuration options for the main script
DEFAULTCONF = {
    "copyfilesto": False,
    "group-types": ["Antivirus"],
    "storage-config": os.path.join(MS_WD, 'storage.ini')
    }

VERBOSE = False

from common import parseDir
from common import parseFileList
from common import parse_config
from common import basename
from common import convert_encoding
from common import queue2list
from common import load_module


class _Print():
    def __init__(self, lock=threading.Lock(), real_print=print):
        self.lock = lock
        self.real_print = real_print

    def __call__(self, *args, **kwargs):
        self.lock.acquire()
        try:
            self.real_print(*args, **kwargs)
        finally:
            self.lock.release()
print = _Print()

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


def _runModule(modname, mod, filelist, threadDict, global_module_interface, conf=None):
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
    mod.print = print

    if not conf:
        try:
            conf = mod.DEFAULTCONF
        except:
            pass

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
        elif VERBOSE:
            print(modname, "failed check(conf)")
    else:
        if mod.check() is True:
            return mod.scan(filelist)
        elif VERBOSE:
            print(modname, "failed check()")


def _get_main_config(config_object, filepath=CONFIG):
    """
    Reads in config for main script. It will write defaults if not present. Returns dictionary.

    Config - The config object
    filepath - The path to the config file
    """
    # Write main defaults if needed
    ConfNeedsWrite = False
    if 'main' not in config_object.sections():
        ConfNeedsWrite = True
        maindefaults = DEFAULTCONF
        config_object.add_section('main')
        for key in maindefaults:
            config_object.set('main', key, str(maindefaults[key]))

    if ConfNeedsWrite:
        conffile = codecs.open(filepath, 'w', 'utf-8')
        config_object.write(conffile)
        conffile.close()
    # Read in main config
    return parse_config(config_object)['main']


def _copy_to_share(filelist, filedic, sharedir):
    """
    Copies files from filelist to a share and populates the filedic. Returns a list of files.

    filelist - The list of file to be copied
    filedic - A dictionary used to translate files back to their original filenames
    sharedir - Where the files are copied to
    """
    if VERBOSE:
        print("Copying files to share...")
    tmpfilelist = filelist[:]
    filelist = []
    for fname in tmpfilelist:
        uid = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        newfile = uid + os.path.basename(fname)
        newfile = newfile.replace(' ', '_')
        filedic[newfile] = fname
        newfile = os.path.join(sharedir, newfile)
        shutil.copyfile(fname, newfile)
        filelist.append(newfile)
    del tmpfilelist
    # Prevents file shares from making modules crash, this might not be the best but meh
    time.sleep(3)
    return filelist


def _start_module_threads(filelist, ModuleList, config, global_module_interface):
    """
    Starts each module on the file list in a separate thread. Returns a list of threads

    filelist - A lists of strings. The strings are files to be scanned
    ModuleList - A list of all the modules to be run
    config - The config dictionary
    global_module_interface - The global module interface to be injected in each module
    """
    if VERBOSE:
        print("Starting modules...")
    ThreadList = []
    ThreadDict = {}
    global_module_interface.run_count += 1
    # Starts a thread for each module.
    for module in ModuleList:
        if module.endswith(".py"):
            modname = os.path.basename(module[:-3])
            moddir = os.path.dirname(module)
            mod = load_module(os.path.basename(module.split('.')[0]), [moddir])
            if not mod:
                print(module, " not a valid module...")
                continue
            conf = None
            if modname in config:
                if '_load_default' in config or '_load_default' in config[modname]:
                    try:
                        conf = mod.DEFAULTCONF
                        conf.update(config[modname])
                    except:
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
                except:
                    pass
            thread = _Thread(target=_runModule, args=(modname, mod, filelist, ThreadDict, global_module_interface, conf))
            thread.name = modname
            thread.setDaemon(True)
            ThreadList.append(thread)
            ThreadDict[modname] = thread
    for thread in ThreadList:
        thread.start()
    return ThreadList


def _write_missing_module_configs(ModuleList, Config, filepath=CONFIG):
    """
    Write in default config for modules not in config file. Returns True if config was written, False if not.

    ModuleList - The list of modules
    Config - The config object
    """
    ConfNeedsWrite = False
    ModuleList.sort()
    for module in ModuleList:
        if module.endswith(".py"):
            modname = os.path.basename(module.split('.')[0])
            moddir = os.path.dirname(module)
            if modname not in Config.sections():
                mod = load_module(os.path.basename(module.split('.')[0]), [moddir])
                if mod:
                    try:
                        conf = mod.DEFAULTCONF
                    except:
                        continue
                    ConfNeedsWrite = True
                    Config.add_section(modname)
                    for key in conf:
                        Config.set(modname, key, str(conf[key]))

    if 'main' not in Config.sections():
        ConfNeedsWrite = True
        Config.add_section('main')
        for key in DEFAULTCONF:
            Config.set('main', key, str(DEFAULTCONF[key]))

    if ConfNeedsWrite:
        conffile = codecs.open(filepath, 'w', 'utf-8')
        Config.write(conffile)
        conffile.close()
        return True
    return False


def _rewite_config(ModuleList, Config, filepath=CONFIG):
    """
    Write in default config for all modules.

    ModuleList - The list of modules
    Config - The config object
    """
    if VERBOSE:
        print("Rewriting config...")
    ModuleList.sort()
    for module in ModuleList:
        if module.endswith(".py"):
            modname = os.path.basename(module.split('.')[0])
            moddir = os.path.dirname(module)
            mod = load_module(os.path.basename(module.split('.')[0]), [moddir])
            if mod:
                try:
                    conf = mod.DEFAULTCONF
                except:
                    continue
                Config.add_section(modname)
                for key in conf:
                    Config.set(modname, key, str(conf[key]))

    Config.add_section('main')
    for key in DEFAULTCONF:
        Config.set('main', key, str(DEFAULTCONF[key]))

    conffile = codecs.open(filepath, 'w', 'utf-8')
    Config.write(conffile)
    conffile.close()


def config_init(filepath, module_list=parseDir(MODULEDIR, recursive=True)):
    """
    Creates a new config file at filepath

    filepath - The config file to create
    """
    Config = configparser.SafeConfigParser()
    Config.optionxform = str
    _rewite_config(module_list, Config, filepath)


def parse_reports(resultlist, groups=[], ugly=True, includeMetadata=False, python=False):
    """Turn report dictionaries into json output. Returns a string.

    resultlist - A list of the scan return values
    groups - A list of modules types that will be grouped together for the report
    ugly - If True the return json will not be formatted
    includeMetadata - If True module metadata will be included in the report
    python - If true a python dictionary is returned instead of a json string
    """
    files = {}
    metadatas = {}
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

# Keep old API compatibility
parseReports = parse_reports


def multiscan(Files, recursive=False, configregen=False, configfile=CONFIG, config=None, module_list=None):
    """
    The meat and potatoes. Returns the list of module results

    Files - A list of files and dirs to be scanned
    recursive - If true it will search the dirs in Files recursively
    configregen - If True a new config file will be created overwriting the old
    configfile - What config file to use. Can be None.
    config - A dictionary containing the configuration options to be used.
    """
    # Redirect stdout to stderr
    stdout = sys.stdout
    sys.stdout = sys.stderr
    # TODO: Make sure the cleanup from this works is something breaks

    # Init some vars
    # If recursive is None we don't parse the file list and take it as is.
    if recursive is not None:
        filelist = parseFileList(Files, recursive=recursive)
    else:
        filelist = Files
    # A list of files in the module dir
    if module_list is None:
        module_list = parseDir(MODULEDIR, recursive=True)
    # A dictionary used for the copyfileto parameter
    filedic = {}
    # What will be the config file object
    config_object = None

    # Read in config
    if configfile:
        config_object = configparser.SafeConfigParser()
        config_object.optionxform = str
        # Regen the config if needed or wanted
        if configregen or not os.path.isfile(configfile):
            _rewite_config(module_list, config_object, filepath=configfile)

        config_object.read(configfile)
        main_config = _get_main_config(config_object, filepath=configfile)
        if config:
            file_conf = parse_config(config_object)
            for key in config:
                if key not in file_conf:
                    file_conf[key] = config[key]
                    file_conf[key]['_load_default'] = True
                else:
                    file_conf[key].update(config[key])
            config = file_conf
        else:
            config = parse_config(config_object)
    else:
        if config is None:
            config = {}
        else:
            config['_load_default'] = True
        if 'main' in config:
            main_config = config['main']
        else:
            main_config = DEFAULTCONF

    # If none of the files existed
    if not filelist:
        sys.stdout = stdout
        raise ValueError("No valid files")

    # Copy files to a share if configured
    if "copyfilesto" not in main_config:
        main_config["copyfilesto"] = False
    if main_config["copyfilesto"]:
        if os.path.isdir(main_config["copyfilesto"]):
            filelist = _copy_to_share(filelist, filedic, main_config["copyfilesto"])
        else:
            sys.stdout = stdout
            raise IOError('The copyfilesto dir" ' + main_config["copyfilesto"] + '" is not a valid dir')

    # Create the global module interface
    global_module_interface = _GlobalModuleInterface()

    # Start a thread for each module
    thread_list = _start_module_threads(filelist, module_list, config, global_module_interface)

    # Write the default configure settings for missing ones
    if config_object:
        _write_missing_module_configs(module_list, config_object, filepath=configfile)

    # Warn about spaces in file names
    for f in filelist:
        if ' ' in f:
            print('WARNING: You are using file paths with spaces. This may result in modules not reporting correctly.')
            break

    # Wait for all threads to finish
    thread_wait_list = thread_list[:]
    i = 0
    while thread_wait_list:
        i += 1
        for thread in thread_wait_list:
            if not thread.is_alive():
                i = 0
                thread_wait_list.remove(thread)
                if VERBOSE:
                    print(thread.name, "took", thread.endtime-thread.starttime)
        if i == 15:
            i = 0
            if VERBOSE:
                p = 'Waiting on'
                for thread in thread_wait_list:
                    p += ' ' + thread.name
                p += '...'
                print(p)
        time.sleep(1)

    # Delete copied files
    if main_config["copyfilesto"]:
        for item in filelist:
            os.remove(item)

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

    # Return stdout to previous state
    sys.stdout = stdout
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
    i = 0
    while thread_wait_list:
        i += 1
        for thread in thread_wait_list:
            if not thread.is_alive():
                i = 0
                thread_wait_list.remove(thread)
                if VERBOSE:
                    print(thread.name, "took", thread.endtime-thread.starttime)
        if i == 15:
            i = 0
            if VERBOSE:
                p = 'Waiting on'
                for thread in thread_wait_list:
                    p += ' ' + thread.name
                p += '...'
                print(p)
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
    import argparse
    # argparse stuff
    parser = argparse.ArgumentParser(description="Analyse files against multiple engines")
    parser.add_argument("-c", "--config", help="The config file to use", required=False, default=CONFIG)
    parser.add_argument('-j', '--json', help="The json file to write", required=False, metavar="filepath", default=None)
    parser.add_argument("-m", "--metadata", help="This will include the metadata section from the report", action="store_true")
    parser.add_argument('-n', '--numberper', help="The max number of files per report", required=False, metavar="num", default=200, type=int)
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively parse folders for files to scan")
    parser.add_argument("-z", "--extractzips", action="store_true", help="If any zip files are detected, extract them and scan the contents")
    parser.add_argument("-p", "--password", help="Password to unzip any archives listed", default="")
    parser.add_argument("-s", "--show", action="store_true", help="Print report to screen")
    parser.add_argument("-u", "--ugly", help="If set the printed json will not have whitespace", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Read in the report file and continue where we left off")
    parser.add_argument('Files', help="Files and Directories to analyse", nargs='+')
    return parser.parse_args()


def _init(args):
    # Initialize configuration file
    if os.path.isfile(args.config):
        print('Warning:', args.config, 'already exists, overwriting will destroy changes')
        answer = raw_input('Do you wish to overwrite the configuration file [y/N]:')
        if answer == 'y':
            config_init(args.config)
            print('Configuration file initialized at', args.config)
        else:
            print('Checking for missing modules in configuration...')
            ModuleList = parseDir(MODULEDIR, recursive=True)
            Config = configparser.SafeConfigParser()
            Config.optionxform = str
            Config.read(args.config)
            _write_missing_module_configs(ModuleList, Config, filepath=args.config)
    else:
        config_init(args.config)
        print('Configuration file initialized at', args.config)

    # Init storage
    Config = configparser.SafeConfigParser()
    Config.optionxform = str
    Config.read(args.config)
    config = _get_main_config(Config)
    if os.path.isfile(config["storage-config"]):
        print('Warning:', config["storage-config"], 'already exists, overwriting will destroy changes')
        answer = raw_input('Do you wish to overwrite the configuration file [y/N]:')
        if answer == 'y':
            storage.config_init(config["storage-config"], overwrite=True)
            print('Storage configuration file initialized at', config["storage-config"])
        else:
            print('Checking for missing modules in storage configuration...')
            storage.config_init(config["storage-config"], overwrite=False)
    else:
        storage.config_init(config["storage-config"])
        print('Storage configuration file initialized at', config["storage-config"])

    exit(0)


def _main():
    # Force all prints to go to stderr
    stdout = sys.stdout
    sys.stdout = sys.stderr
    # Import dependencies only needed by _main()
    import zipfile
    # Get args
    args = _parse_args()
    # Set verbose
    if args.verbose:
        global VERBOSE
        VERBOSE = args.verbose

    # Checks if user is trying to initialize
    if args.Files == ['init'] and not os.path.isfile('init'):
        _init(args)

    if not os.path.isfile(args.config):
        config_init(args.config)

    # Make sure report is not a dir
    if args.json:
        if os.path.isdir(args.json):
            print('ERROR:', args.json, 'is a directory, a file is expected')
            return False

    # Parse the file list
    parsedlist = parseFileList(args.Files, recursive=args.recursive)

    # Unzip zip files if asked to
    if args.extractzips:
        for fname in parsedlist:
            if zipfile.is_zipfile(fname):
                unzip_dir = os.path.join('_tmp', os.path.basename(fname))
                z = zipfile.ZipFile(fname)
                # TODO: Add password capabilities
                if PY3:
                    args.password = bytes(args.password, 'utf-8')
                try:
                    z.extractall(path=unzip_dir, pwd=args.password)
                    for uzfile in z.namelist():
                        parsedlist.append(os.path.join(unzip_dir, uzfile))
                except RuntimeError as e:
                    print("ERROR: Failed to extract ", fname, ' - ', e, sep='')
                parsedlist.remove(fname)

    # Resume from report
    if args.resume:
        i = len(parsedlist)
        try:
            reportfile = codecs.open(args.json, 'r', 'utf-8')
        except Exception as e:
            print("ERROR: Could not open report file")
            exit(1)
        for line in reportfile:
            line = json.loads(line)
            for fname in line:
                if fname in parsedlist:
                    parsedlist.remove(fname)
        reportfile.close()
        i = i - len(parsedlist)
        if VERBOSE:
            print("Skipping", i, "files which are in the report already")

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
        results = multiscan(filelist, recursive=None, configfile=args.config)

        # We need to read in the config for the parseReports call
        Config = configparser.SafeConfigParser()
        Config.optionxform = str
        Config.read(args.config)
        config = _get_main_config(Config)
        # Make sure we have a group-types
        if "group-types" not in config:
            config["group-types"] = []
        elif not config["group-types"]:
            config["group-types"] = []

        # Add in script metadata
        endtime = str(datetime.datetime.now())

        # For windows compatibility
        try:
            username = os.getlogin()
        except:
            username = os.getenv('USERNAME')

        results.append(([], {"Name": "MultiScanner",
            "Start Time": starttime,
            "End Time": endtime,
            # "Command Line":list2cmdline(sys.argv),
            "Run by": username
        }))

        if args.show or not stdout.isatty():
            # TODO: Make this output something readable
            # Parse Results
            report = parse_reports(results, groups=config["group-types"], ugly=args.ugly, includeMetadata=args.metadata)

            # Print report
            try:
                print(convert_encoding(report, encoding='ascii', errors='replace'), file=stdout)
                stdout.flush()
            except Exception as e:
                print('ERROR: Can\'t print report -', e)

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
