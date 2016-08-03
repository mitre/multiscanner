# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import ast
import sys
import imp
import configparser
PY3 = False
if sys.version_info > (3,):
    PY3 = True
try:
    import paramiko
    SSH = True
except:
    SSH = False

def load_module(name, path):
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

def list2cmdline(list):
    """
    This is used to overwrite the default subprocess list2cmdline function.
    
    The default subprocess list2cmdline function on windows messes with quotes arguments. This will not
    """
    return ' '.join(list)

def convert_encoding(data, encoding='UTF-8', errors='replace'):
    """
    Converts dicts, lists, and strs to the encoding. It uses data.decode to do this.

    data - The data to be converted
    encoding - The encoding method to use
    error - The codec error handling method to use
    """
    if isinstance(data, dict):
        if PY3:
            return dict((convert_encoding(key), convert_encoding(value)) for key, value in data.items())
        else:
            return dict((convert_encoding(key), convert_encoding(value)) for key, value in data.iteritems())
    elif isinstance(data, list):
        return [convert_encoding(element) for element in data]
    elif isinstance(data, str):
        if PY3:
            # I think this works?
            return str(data.encode(encoding=encoding, errors=errors), encoding)
        else:
            return data.decode(encoding, errors)
    else:
        return data

def parse_config(config_object):
    """Take a config object and returns it as a dictionary"""
    return_var = {}
    for section in config_object.sections():
        section_dict = dict(config_object.items(section))
        for key in section_dict:
            try:
                section_dict[key] = ast.literal_eval(section_dict[key])
            except:
                pass
        return_var[section] = section_dict
    return return_var

def get_storage_config_path(config_file):
    """Gets the location of the storage config file from the multiscanner config file"""
    conf = configparser.SafeConfigParser()
    conf.read(config_file)
    conf = parse_config(conf)
    return conf['main']['storage-config']

def dirname(path):
    """OS independent version of os.path.dirname"""
    split = path.split('/')
    if len(split) > 1:
        return '/'.join(split[:-1])
    else:
        split = path.split('\\')
        return '\\'.join(split[:-1])

def basename(path):
    """OS independent version of os.path.basename"""
    if path.endswith('/') or path.endswith('\\'):
        path = path[:-1]
    split = path.split('/')
    if len(split) > 1:
        return split[-1]
    else:
        split = path.split('\\')
        return split[-1]
    
def parseDir(directory, recursive=False):
    """
    Returns a list of files in a directory.
    
    dir - The directory to search
    recursive - If true it will recursively find files.
    """
    filelist = []
    for item in os.listdir(directory):
        item = os.path.join(directory, item)
        if os.path.isdir(item):
            if recursive:
                filelist.extend(parseDir(item, recursive))
            else:
                continue
        else:
            filelist.append(item)
    return filelist
    
def parseFileList(FileList, recursive=False):
    """
    Takes a list of files and directories and returns a list of files.
    
    FileList - A list of files and directories. Files in each directory will be returned
    recursive - If true it will recursively find files in directories.
    """
    filelist = []
    for item in FileList:
        if os.path.isdir(item):
            filelist.extend(parseDir(item, recursive))
        elif os.path.isfile(item):
            filelist.append(item)
        else:
            pass
    return filelist

def chunk_file_list(filelist, cmdlength=7191):
    """
    Takes the file list and splits it into chunks so windows won't break. Returns a list of lists of strings.
    
    filelist - The list to be chunked
    cmdlength - Max length of all filenames appended to each other
    """
    #This fixes if the cmd line would be far too long
    #8191 is the windows limit
    filechunks = []
    if len(list2cmdline(filelist)) >= cmdlength:
        filechunks.append(filelist[:len(filelist)/2])
        filechunks.append(filelist[len(filelist)/2:])
        #Keeps splitting chunks until all are correct size
        splitter = True
        while splitter:
            splitter = False
            for chunk in filechunks[:]:
                if len(list2cmdline(chunk)) >= cmdlength:
                    filechunks.remove(chunk)
                    filechunks.append(chunk[:len(chunk)/2])
                    filechunks.append(chunk[len(chunk)/2:])
                    splitter = True
    else:
        filechunks = [filelist]
    return filechunks

def queue2list(queue):
    """Takes a queue a returns a list of the elements in the queue."""
    list = []
    while not queue.empty():
        list.append(queue.get())
    return list
    
def hashfile(fname, hasher, blocksize=65536):
    """
    Hashes a file in chunks and returns the hash algorithms digest.
    
    fname - The file to be hashed
    hasher - The hasher from hashlib. E.g. hashlib.md5()
    blocksize - The size of each block to read in from the file
    """
    afile = open(fname, 'rb')
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    afile.close()
    return hasher.hexdigest()

def sshconnect(hostname, port=22, username=None, password=None, pkey=None, key_filename=None, timeout=None, allow_agent=True, look_for_keys=True, compress=False, sock=None):
    """A wrapper for paramiko, returns a SSHClient after it connects."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password, pkey=pkey, key_filename=key_filename, timeout=timeout, allow_agent=allow_agent, look_for_keys=look_for_keys, compress=compress, sock=sock)
    return client
        
def sessionexec(client, cmd):
    """Creates a session object and executes a command. Returns the session object"""
    session = client.get_transport().open_session()
    session.exec_command(cmd)
    return session
    
def sshexec(hostname, cmd, port=22, username=None, password=None, key_filename=None):
    """Connects and runs a command. Returns the contents of stdin."""
    client = sshconnect(hostname, port=port, username=username, password=password, key_filename=key_filename)
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read()

