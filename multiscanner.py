#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import sys
import os
import imp
import json
import re
import shutil
import time
import datetime
import random
import string
import threading

PY3 = False
if sys.version_info < (2, 7) or sys.version_info > (4,):
    print("WARNING: You're running an untested version of python")
elif sys.version_info > (3,):
    PY3 = True

if PY3:
    import configparser as ConfigParser
    raw_input = input
else:
    import ConfigParser

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
    "group-types": ["Antivirus"]
    }

VERBOSE = False

from common import parseDir
from common import parseFileList
from common import conf2dic
from common import basename
from common import convert_encoding

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


def _loadModule(name, path):
    """
    Loads a module by filename and path. Returns module object

    name - Filename without .py
    path - A list of dirs to search
    """
    try:
        (fname, pathname, description) = imp.find_module(name, path)
        loaded_mod = imp.load_module(name, fname, pathname, description)
    except Exception as e:
        loaded_mod = None
        print(e)

    return loaded_mod


def _runModule(modname, mod, filelist, threadDict, conf=None):
    """
    Runs a module on a file list.
    
    Modules are loaded and check is called followed by scan.
    modname - The name of the module
    mod - The imported module
    filelist - The list of files on the host to be scanned
    threadDict - A dictionary of all threads. {modname: Thread}
    conf - The config to be passed to the module. If None it will try to use the default conf
    """

    # Try and read in the default conf if one was not passed
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
        threadDict[reqmodname].starttime = time.time()

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


def _get_main_config(Config, filepath=CONFIG):
    """
    Reads in config for main script. It will write defaults if not present. Returns dictionary.
    
    Config - The config object
    filepath - The path to the config file
    """
    # Write main defaults if needed
    ConfNeedsWrite = False
    if 'main' not in Config.sections():
        ConfNeedsWrite = True
        maindefaults = DEFAULTCONF
        Config.add_section('main')
        for key in maindefaults:
            Config.set('main', key, maindefaults[key])
    
    if ConfNeedsWrite:
        conffile = open(filepath, 'w')
        Config.write(conffile)
        conffile.close()
    # Read in main config
    return conf2dic(Config.items('main'))


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
        filedic[newfile] = fname
        newfile = os.path.join(sharedir, newfile)
        shutil.copyfile(fname, newfile)
        filelist.append(newfile)
    del tmpfilelist	
    # Prevents file shares from making modules crash, this might not be the best but meh
    time.sleep(3)
    return filelist


def _start_module_threads(filelist, ModuleList, Config):
    """
    Starts each module on the file list in a separate thread. Returns a list of threads
    
    filelist - A lists of strings. The strings are files to be scanned
    ModuleList - A list of all the modules to be run
    Config - The config object
    """
    if VERBOSE:
        print("Starting modules...")
    ThreadList = []
    ThreadDict = {}
    # Starts a thread for each module. 
    for module in ModuleList:
        if module.endswith(".py"):
            modname = os.path.basename(module[:-3])
            mod = _loadModule(os.path.basename(module.split('.')[0]), [MODULEDIR])
            if not mod:
                print(module, " not a valid module...")
                continue
            conf = None
            if modname in Config.sections():
                conf = conf2dic(Config.items(modname))
            thread = _Thread(target=_runModule, args=(modname, mod, filelist, ThreadDict, conf))
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
    for module in ModuleList:
        if module.endswith(".py"):
            modname = os.path.basename(module.split('.')[0])
            if modname not in Config.sections():
                mod = _loadModule(os.path.basename(module.split('.')[0]), [MODULEDIR])
                if mod:
                    try:
                        conf = mod.DEFAULTCONF
                    except:
                        continue
                    ConfNeedsWrite = True
                    Config.add_section(modname)
                    for key in conf:
                        Config.set(modname, key, conf[key])

    if 'main' not in Config.sections():
        ConfNeedsWrite = True
        Config.add_section('main')
        for key in DEFAULTCONF:
            Config.set('main', key, DEFAULTCONF[key])

    if ConfNeedsWrite:
        conffile = open(filepath, 'w')
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
    for module in ModuleList:
        if module.endswith(".py"):
            modname = os.path.basename(module.split('.')[0])
            mod = _loadModule(os.path.basename(module.split('.')[0]), [MODULEDIR])
            if mod:
                try:
                    conf = mod.DEFAULTCONF
                except:
                    continue
                Config.add_section(modname)
                for key in conf:
                    Config.set(modname, key, conf[key])

    Config.add_section('main')
    for key in DEFAULTCONF:
        Config.set('main', key, DEFAULTCONF[key])

    conffile = open(filepath, 'w')
    Config.write(conffile)
    conffile.close()


def config_init(filepath):
    """
    Creates a new config file at filepath

    filepath - The config file to create
    """
    Config = ConfigParser.ConfigParser()
    Config.optionxform = str
    ModuleList = parseDir(MODULEDIR)
    _rewite_config(ModuleList, Config, filepath)


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
        return json.dumps(finaldata, sort_keys=True, indent=3)
    else:
        return json.dumps(finaldata, sort_keys=True, separators=(',', ':'))

# Keep old API compatibility
parseReports = parse_reports

def multiscan(Files, recursive=False, configregen=False, configfile=CONFIG):
    """
    The meat and potatoes. Returns the list of module results
    
    Files - A list of files and dirs to be scanned
    recursive - If true it will search the dirs in Files recursively
    configregen - If True a new config file will be created overwriting the old
    configfile - What config file to use
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
    # TODO: This should just be a list of .py's that is passed
    ModuleList = parseDir(MODULEDIR)
    # A dictionary used for the copyfileto parameter
    filedic = {}
    
    # Read in config file
    Config = ConfigParser.ConfigParser()
    Config.optionxform = str
    # Regen the config if needed or wanted
    if configregen or not os.path.isfile(configfile):
        _rewite_config(ModuleList, Config, filepath=configfile)
    Config.read(configfile)
    config = _get_main_config(Config, filepath=configfile)
    
    # If none of the files existed
    if not filelist:
        sys.stdout = stdout
        raise ValueError("No valid files")

    # Copy files to a share if configured
    if "copyfilesto" not in config:
        config["copyfilesto"] = False
    if config["copyfilesto"]:
        if os.path.isdir(config["copyfilesto"]):
            filelist = _copy_to_share(filelist, filedic, config["copyfilesto"])
        else:
            sys.stdout = stdout
            raise IOError('The copyfilesto dir" ' + config["copyfilesto"] + '" is not a valid dir')

    # Start a thread for each module
    ThreadList = _start_module_threads(filelist, ModuleList, Config)
    
    # Write the default configure settings for missing ones
    _write_missing_module_configs(ModuleList, Config, filepath=configfile)
    
    # Wait for all threads to finish
    for thread in ThreadList:
        thread.join()

    if VERBOSE:
        for thread in ThreadList:
            print(thread.name, "took", thread.endtime-thread.starttime)
        
    # Delete copied files
    if config["copyfilesto"]:
        for item in filelist:
            os.remove(item)

    # Get Result list
    results = []
    for thread in ThreadList:
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
                # This is ugly but os.path.basename is os dependent
                base = filename.split("\\")[-1].split("/")[-1]
                if base in filedic:
                    filename = filedic[base]
                    modded = True
                    result[j] = (filename, hit)
            if modded:
                results[i] = (result, metadata)

    # Return stdout to previous state
    sys.stdout = stdout
    return results


def _parse_args():
    """
    Parses arguments
    """
    import argparse
    # argparse stuff
    parser = argparse.ArgumentParser(description="Analyse files against multiple engines")
    parser.add_argument("-c", "--config", help="The config file to use", required=False, default=CONFIG)
    parser.add_argument('-j', '--json', help="The json file to write", required=False, metavar="filepath", default='report.json')
    parser.add_argument("-m", "--metadata", help="This will include the metadata section from the report", action="store_true")
    parser.add_argument('-n', '--numberper', help="The max number of files per report", required=False, metavar="num", default=200, type=int)
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively parse folders for files to scan")
    parser.add_argument("-z", "--extractzips", action="store_true", help="If any zip files are detected, extract them and scan the contents")
    parser.add_argument("-p", "--password", help="Password to unzip any archives listed", default="")
    parser.add_argument("-q", "--quiet", action="store_true", help="Do not print report to screen")
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
            ModuleList = parseDir(MODULEDIR)
            Config = ConfigParser.ConfigParser()
            Config.optionxform = str
            Config.read(args.config)
            _write_missing_module_configs(ModuleList, Config, filepath=args.config)
    else:
        config_init(args.config)
        print('Configuration file initialized at', args.config)
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
        VERBOSE = args.verbose

    # Checks if user is trying to initialize
    if args.Files == ['init'] and not os.path.isfile('init'):
        _init(args)

    if not os.path.isfile(args.config):
        config_init(args.config)

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
            reportfile = open(args.json, 'r')
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
        Config = ConfigParser.ConfigParser()
        Config.optionxform = str
        Config.read(args.config)
        config = _get_main_config(Config)

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

        report = None
        if not args.quiet and stdout.isatty():
            # TODO: Make this output something readable
            # Parse Results
            if "group-types" not in config:
                config["group-types"] = []
            elif not config["group-types"]:
                config["group-types"] = []
            report = parse_reports(results, groups=config["group-types"], ugly=args.ugly, includeMetadata=args.metadata)

            # Print report and write to file
            print(report, file=stdout)

        if not stdout.isatty():
            report = parse_reports(results, groups=config["group-types"], ugly=True, includeMetadata=args.metadata)
            print(report, file=stdout)
            stdout.flush()
            # Don't write the default location if we are redirecting output
            if args.json == 'report.json':
                print('Not writing results to report.json, pick a different filename to override')
            else:
                try:
                    reportfile = open(args.json, 'a')
                    reportfile.write(report)
                    reportfile.write('\n')
                    reportfile.close()
                except Exception as e:
                    print(e)
                    print("ERROR: Could not write report file, report not saved")
                    exit(2)
        else:
            # Check if we need to run the report again
            if report is not None and args.ugly is True:
                pass
            else:
                report = parse_reports(results, groups=config["group-types"], ugly=True, includeMetadata=args.metadata)
            # Try to write report
            try:
                reportfile = open(args.json, 'a')
                reportfile.write(report)
                reportfile.write('\n')
                reportfile.close()
            except Exception as e:
                print(e)
                print("ERROR: Could not write report file, report not saved")
                exit(2)

    # Cleanup zip extracted files
    if args.extractzips:
        shutil.rmtree('_tmp')

if __name__ == "__main__":
    _main()
