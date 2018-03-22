Developing an Analysis Module
=============================

Modules are intended to be quickly written and incorporated into the MultiScanner framework. A module must be in the modules folder for it to be used on the next run. The configuration file does not need to be manually updated.

See this :ref:`example`.

Mandatory Functions
-------------------

When writing a new module, two mandatory functions must be defined: check() and scan(). Additional functions can be written as required.

check()
^^^^^^^

The check() function tests whether or not the scan function should be run.

**Inputs:** There are two supported argument sets with this function: ``check()`` and ``check(conf=DEFAULTCONF)``. If a module has a global variable DEFAULTCONF, the second argument set is required.

**Outputs:** The return value of the check() function is a boolean (True or False). A True return value indicated the scan() function should be run; a False return value indicates the module should no longer be run.

scan()
^^^^^^
The scan() function performs the analytic and returns the results.

**Inputs:** There are two supported argument sets with this function: ``scan(filelist)`` and ``scan(filelist, conf=DEFAULTCONF)``. If a module has a global variable DEFAULTCONF, the second argument set is required.

**Outputs:** There are two return values of the scan() function: Results and Metadata (i.e., ``return (Results, Metadata)``).

- **Results** is a list of tuples, the tuple values being the filename and the corresponding scan results (e.g.,``[("file1.exe", "Executable"), ("file2.jpg", "Picture")]``).

- **Metadata** is a dictionary of metadata information from the module. There are two required pieces of metadata ``Name`` and ``Type``. ``Name`` is the name in the module and will be used in the report. ``Type`` is what type of module it is (e.g., Antivirus, content detonation). This information is used for a grouping feature in the report generation and provides context to a newly written module. Optionally, metadata information can be disabled and not be included in the report by setting ``metadata["Include"] = False``.

Special Globals
---------------

There are two global variables that when present, affect the way the module is called.

**DEFAULTCONF** - This is a dictionary of configuration settings. When set, the settings will be written to the configuration file, making it user editable. The configuration object will be passed to the module's check and scan function and must be an argument in both functions.

**REQUIRES** - This is a list of analysis results required by a module. For example, ``REQUIRES = ['MD5']`` will be set to the output from the module MD5.py. An :ref:`example` is provided.

Module Interface
----------------

The module interface is a class that is put into each module as it is run. This allows for several features to be added for interacting with the framework at runtime. It is injected as `multiscanner` in the global namespace.

Variables
^^^^^^^^^

* ``write_dir`` - This is a directory path that the module can write to. This will be unique for each run.
* ``run_count`` - This is an integer that increments for each subscan that is called. It is useful for preventing infinite recursion.

Functions
^^^^^^^^^

* ``apply_async(func, args=(), kwds={}, callback=None)`` - This mirrors multiprocessing.Pool.apply_async and returns a `multiprocessing.pool.AsyncResult <https://docs.python.org/2/library/multiprocessing.html#multiprocessing.pool.AsyncResult>`_. The pool is shared by all modules.
* ``scan_file(file_path, from_filename)`` - This will scan a file that was found inside another file. `file_path` should be the extracted file on the filesystem (you can write it in path at `multiscanner.write_dir`). `from_filename` is the file it was extracted from.

Configuration
-------------

If a module requires configuration, the DEFAULTCONF global variable must be defined. This variable is passed to both check() and scan(). The configuration will be read from the configuration file if it is present. If the file is not present, it will be written into the configuration file.

If ``replacement path`` is set in the configuration, the module will receive file names, with the folder path replaced with the variable's value. This is useful for analytics which are run on a remote machine.

By default, ConfigParser reads everything in as a string, before options are passed to the module and ``ast.literal_eval()`` is run on each option. If a string is not returned when expected, this is why. This does mean that the correct Python type will be returned instead of all strings.
