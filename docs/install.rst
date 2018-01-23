Installation
============

Installation information for the different components of MultiScanner is provided below. To get an idea of how the system works without going through the full process of setting up the distributed architecture, refer to the section on :ref:`standalone-docker-installation`. 

The Docker standalone system is less scalable, robust, and feature-rich, but it enables easy stand up the web UI, the REST API, and an Elasticsearch node, allowing users to quickly see how the system works. The standalone container is intended as an introduction to the system and its capabilities, but is not designed for operational use.

System Requirements
-------------------

Python 3.6 is recommended. Compatibility with Python 2.7+ and 3.4+ is supported but not thoroughly maintained and tested. Please submit an issue or a pull request fixing any issues found with other versions of Python.

An installer script is included in the project (`install.sh <https://github.com/mitre/multiscanner/blob/feature-celery/install.sh>`_), which installs the prerequisites on most systems.

Currently, MultiScanner is deployed with Ansible, and we're working to support distributed architecture deployment via Docker. 

Installing Ansible
------------------

The `installer script <https://github.com/mitre/multiscanner/blob/feature-celery/install.sh>`_ should install the required Python packages for users of RedHat- or Debian-based Linux distributions. Users of other distributions should refer to `requirements.txt <https://github.com/mitre/multiscanner/blob/feature-celery/requirements.txt>`_.

MultiScanner requires a configuration file to run. After cloning the repository, generate the MultiScanner default
configuration by running ``python multiscanner.py init``. The command can be used to rewrite the configuration file to its default state or, if new modules have been written, to add their configuration details to the configuration
file.

.. _installing-analytic-machines:

Installing Analytic Machines
----------------------------

Default modules have the option of being run locally or via SSH. The development team
runs MultiScanner on a Linux host and hosts the majority of analytical tools on
a separate Windows machine. The SSH server used in this environment is `freeSSHd <http://www.freesshd.com/>`_. 

A network share accessible to both the MultiScanner and the analytic machines is
required for the multi-machine setup. Once configured, the network share path must
be identified in the configuration file, config.ini. To do this, set the ``copyfilesto``
option under ``[main]`` to be the mount point on the system running MultiScanner.
Modules can have a ``replacement path`` option, which is the network share mount point
on the analytic machine.

Installing Elasticsearch
------------------------

Starting with Elasticsearch 2.x, field names can no longer contain '.' (dot) characters. Thus, the MultiScanner elasticsearch_storage module adds a pipeline called "dedot" with a processor to replace dots in field names with underscores.

Add the following to the elasticsearch.yml configuration file for the dedot processor to work::

    script.painless.regex.enabled: true


To use the Multiscanner web UI, also add the following::

    http.cors.enabled: true
    http.cors.allow-origin: "<yourOrigin>"

..
	
.. _module-config:
	
Module Configuration
--------------------

Modules are intended to be quickly written and incorporated into the framework. Note that:

* A finished module must be placed in the modules folder before it can be used. 

* The configuration file does not need to be manually updated.

* Modules are configured within the configuration file, `config.ini <https://github.com/mitre/multiscanner/blob/feature-celery/docker_utils/config.ini>`_. 

Parameters common to all modules are listed in the next section, and module-specific parameters (for core and analysis modules that have parameters) are listed in the subsequent sections. See :ref:`analysis-modules` for information about *all* current modules.

Common Parameters
^^^^^^^^^^^^^^^^^

The parameters below may be used by all modules.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*path*                Location of the executable.
*cmdline*             An array of command line options to be passed to the executable.
*host*                The hostname, port, and username of the machine that will be SSH’d into to run the analytic if the executable is not present on the local machine.
*key*                 The SSH key to be used to SSH into the host.
*replacement path*    If the main config is set to copy the scanned files this will be what it replaces the path with. It should be where the network share is mounted. 
*ENABLED*             When set to false, the module will not run.
====================  =============================

Parameters of Core Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^

**[main]** - searches virustotal for a file hash and downloads the report, if available.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*copyfilesto*         This is where the script will copy each file that is to be scanned. This can be removed or set to False to disable this feature.
*group-types*         This is the type of analytics to group into sections for the report. This can be removed or set to False to disable this feature.
*storage-config*      Path to the storage config file.
*api-config*          Path to the API config file.
*web-config*          Path to the Web UI config file.
====================  =============================

Parameters of Analysis Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Analysis modules with additional parameters (or notes for installation) are given below in alphabetical order. See :ref:`analysis-modules` for a list of all current analysis modules.

**[Cuckoo]** - submits a file to a Cuckoo Sandbox cluster for analysis.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*API URL*             The URL to the API server.
*WEB URL*             The URL to the Web server.
*timeout*             The maximum time a sample will run.
*running timeout*     An additional timeout, if a task is in the running state this many seconds past *timeout*, the task is considered failed.
*delete tasks*        When set to True, tasks will be deleted from Cuckoo after detonation. This is to prevent filling up the Cuckoo machine's disk with reports.
*maec*                When set to True, a `MAEC <https://maecproject.github.io>`_ JSON-based report is added to Cuckoo JSON report. *NOTE*: Cuckoo needs MAEC reporting enabled to produce results.
====================  =============================

**[ExifToolsScan]** - scans the file with Exif tools and returns the results.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*remove-entry*        A Python list of ExifTool results that should not be included in the report. File system level attributes are not useful and stripped out.
====================  =============================

**[FireeyeAPI]** - detonates the sample in FireEye AX via FireEye's API. This "API" version replaces the "FireEye Scan" module.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*API URL*             The URL to the API server.
*fireeye images*      A Python list of the VMs in fireeye. These are used to generate where to copy the files.
*username*            Username on the FireEye AX. 
*password*            Password for the FireEye AX.
*info level*          Options are concise, normal, and extended.
*timeout*             The maximum time a sample will run.
*force*               If set to True, will rescan if the sample matches a previous scan.
*analysis type*       0 = sandbox, 1 = live.
*application id*      For AX Series appliances (7.7 and higher) and CM Series appliances that manage AX Series appliances (7.7 and higher), setting the application value to -1 allows the AX Series appliance to choose the application. For other appliances, setting the application value to 0 allows the AX Series appliance to choose the application.
====================  =============================

**[libmagic]** - runs libmagic against the files.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*magicfile*           The path to the compiled magic file you wish to use. If None it will use the default one.
====================  =============================

**[Metadefender]** - runs Metadefender against the files.

.. tabularcolumns:: |p{3cm}|p{12cm}|

======================  =============================
Parameter               Description
======================  =============================
*timeout*               The maximum time a sample will run.
*running timeout*       An additional timeout, if a task is in the running state this many seconds past *timeout*, the task is considered failed.
*fetch delay seconds*   The number of seconds for the module to wait between submitting all samples and polling for scan results. Increase this value if Metadefender is taking a long time to store the samples.
*poll interval*         The number of seconds between successive queries to Metadefender for scan results. Default is 5 seconds.
*user agent*            Metadefender user agent string, refer to your Metadefender server configuration for this value. Default is "user agent".
======================  =============================

**[NSRL]** - looks up hashes in the NSRL database. These two parameters are automatically generated. Users must run nsrl_parse.py tool in the utils/ directory before using this module.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*hash_list*           The path to the NSRL database on the local filesystem, containing the MD5 hash, SHA1 hash, and original file name.
*offsets*             A file that contains the pointers into hash_list file. This is necessary to speed up searching of the NSRL database file.
====================  =============================

**[PEFile]** - extracts out feature information from EXE files. 

* The module uses `pefile <https://code.google.com/p/pefile/>`_ which is currently not available for Python 3.

**[Tika]** - extracts metadata from the file using `Tika <https://tika.apache.org/>`_. For configuration of the module see the `tika-python <https://github.com/chrismattmann/tika-python/blob/master/README.md>`_ documentation.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*remove-entry*        A Python list of Tika results that should not be included in the report.
====================  =============================

**[TrID]** - runs `TrID <http://mark0.net/soft-trid-e.html>`_ against a file. 

* The module definition file must be in the same folder as the executable malware sample.

**[vtsearch]** - searches `virustotal <https://www.virustotal.com/>`_ for the files hash and download the report if available.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*apikey*              Public/private api key. Can optionally make it a list and the requests will be distributed across them. This is useful when two groups with private api keys want to share the load and reports.
====================  =============================

**[VxStream]** - submits a file to a VxStream Sandbox cluster for analysis.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*BASE URL*            The base URL of the VxStream server.
*API URL*             The URL to the API server (include the /api/ in this URL).
*API Key*             The user's API key to the API server.
*API Secret*          The user's secret to the API server.
*Environment ID*      The environment in which to execute the sample (if you have different sandboxes configured).
*Verify*              Set to false to ignore TLS certificate errors when querying the VxStream server.
*timeout*             The maximum time a sample will run
*running timeout*     An additional timeout, if a task is in the running state this many seconds past *timeout*, the task is considered failed.
====================  =============================

**[YaraScan]** - scans the files with yara and returns the results; yara-python must be installed.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
*ruledir*             The directory to look for rule files in.
*fileextensions*      A Python array of all valid rule file extensions. Files not ending in one of these will be ignored.
*ignore-tags*         A Python array of yara rule tags that will not be included in the report.
====================  =============================

.. _standalone-docker-installation:

Standalone Docker Installation
------------------------------

To introduce new users to the power of the MultiScanner framework, web UI, and REST API, we have built a standalone docker application that is simple to run in new environments. Simply clone the top level directory and run::

    $ docker-compose up

This will build the three necessary containers (one for the web application, one for the REST API, and one for the Elasticsearch backend).

Running this command will generate a lot of output and take some time. The system is not ready until you see the following output in your terminal::

    api_1      |  * Running on http://0.0.0.0:8080/ (Press CTRL+C to quit)

.. note::  THIS CONTAINER IS NOT DESIGNED FOR PRODUCTION USE. This is simply a primer for using MultiScanner's web interface. The MultiScanner framework is highly scalable and distributed, but it requires a full install. Currently, we support installing the distributed system via Ansible. More information about that process can be found here: `<https://github.com/mitre/multiscanner-ansible>`_.
	
.. note:: The latest versions of docker and docker-compose are assumed to be installed. Installation guides are here: https://docs.docker.com/engine/installation/ and here: https://docs.docker.com/compose/install/

.. note:: Because this docker container runs two web applications and an Elasticsearch node, there is a fairly high requirement for computing power (RAM). We recommend running this on a machine with at least 4GB of RAM.

.. note:: This container will only be reachable and functionable on localhost.

.. note:: The docker-compose.yml file must be edited in four places if the system is installed behind a proxy. First, uncomment `lines 18-20 <https://github.com/mitre/multiscanner/blob/feature-celery/docker-compose.yml#L18>`_ and `lines 35-37 <https://github.com/mitre/multiscanner/blob/feature-celery/docker-compose.yml#L35>`_. Next, uncomment `lines 25-28 <https://github.com/mitre/multiscanner/blob/feature-celery/docker-compose.yml#L25>`_ and set the correct proxy variables. Finally, do the same thing in `lines 42-45 <https://github.com/mitre/multiscanner/blob/feature-celery/docker-compose.yml#L42>`_. The docker-compose.yml file has comments to make clear where to make these changes.
