MultiScanner 
==============

Introduction
------------
MultiScanner is a framework that allows the user to evaluate a set of files with a custom build of analytical tools. These tools are incorporated as modules into the MultiScanner framework. Modules are designed to be quickly written and easily incorporated into the framework. Current modules are related to malware analytics, but the framework is not limited to that scope.

Requirements
------------
Python >= 2.7 should be used. Python 3 is partially supported; some modules may not work in Python 3.

Requirements can be installed by running `pip install -r requirements.txt` after cloning the repo. `pip install -r requirements3.txt` should be run for python 3. [Yara-python](http://yara.readthedocs.org/en/latest/yarapython.html) will need to be installed manually.

Installation
------------
### MultiScanner ###
Generate the MultiScanner default configuration by running `python multiscanner.py init` after cloning the repository. This can be used to rewrite the configuration file to its default state or, if you add new modules to add their configuration to the configuration file.

### Analytic Machine ###
Default modules have the option to be run locally or via SSH. The environment used by the development team runs MultiScanner on a Linux host and hosts the majority of analytical tools on a separate Windows 
machine. The SSH server used in this environment is freeSSHd from [http://www.freesshd.com/](http://www.freesshd.com/).
 
A network share that both the MultiScanner and the Analytic Machine can access is required for this type of setup. Once configured, the network share path must be identified in the configuration file, config.ini. To do this set the `copyfilesto` option under `[main]` to be the mount point on the system running MultiScanner. Modules can have a `replacement path` option, which is the network share mount point on the analytic machine.

Module Writing
--------------
Modules are intended to be quickly written and incorporated into the framework. A finished module must be placed in the modules folder for it to be used on the next run.
See [docs/module_writing.md](docs/module_writing.md) for more information.

Module Configuration
-------------
Enable modules by including them in the configuration file, config.ini. See [docs/modules.md](docs/modules.md) for more information.

Use in other projects
---------------------
MultiScanner can be incorporated as a module in another projects. Below is the simplest example of how to import MultiScanner into a Python script.

```python
import multiscanner
output = multiscanner.multiscan(FileList)
Results = multiscanner.parseReports(output, python=True)
```

Results is a dictionary object where each key is a filename of a scanned file.

`multiscanner.config_init(filepath)` will create a default configuration file at the location defined by filepath.

Other Reading
-------------
For more information on module configuration or writing modules check the [docs](docs) folder.
Test commit.