.. _analysis-modules:

Analysis Modules
================

The analysis modules currently available in MultiScanner are listed by catagory below.

.. tabularcolumns:: |p{4cm}|p{11cm}|

==============================  ========================================
AV Scans
==============================  ========================================
:ref:`AVG 2014 <mod-avg-2014>`  Scans sample with AVG 2014
:ref:`ClamAVScan <mod-clamav>`  Scans sample with ClamAV
:ref:`McAfeeScan <mod-mcafee>`  Scans sample with McAfee AntiVirus Command Line
Microsoft Security Essentials   Scans sample with Microsoft Security Essentials
Metadefender                    Interacts with OPSWAT Metadefender Core 4 Version 3.x, polling Metadefender for scan results.
:ref:`vtsearch <mod-vtsearch>`  Searches VirusTotal for sample’s hash and downloads the report if available
VFind                           Runs the CyberSoft VFind anti-malware scanner, part of the `VFind Security Toolkit <https://www.cybersoft.com/products/vstk/>`_.
==============================  ========================================

.. tabularcolumns:: |p{3cm}|p{12cm}|

=============================  ========================================
Database
=============================  ========================================
NSRL                           Looks up a hash in the `National Software Reference Library <https://www.nist.gov/software-quality-group/national-software-reference-library-nsrl>`_.
=============================  ========================================

.. tabularcolumns:: |p{4cm}|p{11cm}|

===================================  ========================================
Sandbox Detonation
===================================  ========================================
:ref:`Cuckoo Sandbox <mod-cuckoo>`   Submits a sample to Cuckoo Sandbox cluster for analysis.
FireEye API                          Detonates the sample in FireEye AX via FireEye's API.
:ref:`VxStream <mod-vxstream>`       Submits a file to a VxStream Sandbox cluster for analysis.
===================================  ========================================

.. tabularcolumns:: |p{3cm}|p{12cm}|

=============================  ========================================
Machine Learning
=============================  ========================================
MaliciousMacroBot              Triage office files with `MaliciousMacroBot <https://github.com/egaus/MaliciousMacroBot>`_.
=============================  ========================================

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================================  ========================================
Metadata
====================================  ========================================
entropy                               Calculates the Shannon entropy of a file.
:ref:`ExifToolsScan <mod-exiftools>`  Scans sample with Exif tools and returns the results.
fileextensions                        Determines possible file extensions for a file.
:ref:`floss <mod-floss>`              FireEye Labs Obfuscated String Solver uses static analysis techniques to deobfuscate strings from malware binaries. [floss]|
:ref:`impfuzzy <mod-impfuzzy>`        Calculates a fuzzy hash using ssdeep on Windows PE imports.
:ref:`libmagic <mod-libmagic>`        Runs libmagic against the files to identify filetype.
:ref:`MD5 <mod-md5>`                  Generates the MD5 hash of the sample.
:ref:`officemeta <mod-officemeta>`    Extracts metadata from Microsoft Office documents.
:ref:`pdfinfo <mod-pdfinfo>`          Extracts feature information from PDF files using `pdf-parser <http://blog.didierstevens.com/programs/pdf-tools/>`_.
:ref:`PEFile <mod-pefile>`            Extracts features from EXE files.
pehasher                              Computes pehash values using a variety of algorithms: totalhase, anymaster, anymaster_v1_0_1, endgame, crits, and pehashng.|
SHA1                                  Generates the SHA1 hash of the sample.
:ref:`SHA256 <mod-sha256>`            Generates the SHA256 hash of the sample.
:ref:`ssdeep <mod-ssdeeper>`          Generates context triggered piecewise hashes (CTPH) for files. More information can be found on the `ssdeep website <http://ssdeep.sourceforge.net/>`_.
:ref:`Tika <mod-tika>`                Extracts metadata from the sample using `Tika <https://tika.apache.org/)>`__.
:ref:`TrID <mod-trid>`                Runs `TrID <http://mark0.net/soft-trid-e.html)>`__ against a file.
UAD                                   Runs the CyberSoft Universal Atomic Disintegrator (UAD) tool, part of the `VFind Security Toolkit <https://www.cybersoft.com/products/vstk/>`_.
====================================  ========================================

.. tabularcolumns:: |p{3cm}|p{12cm}|

=============================  ========================================
Signatures
=============================  ========================================
:ref:`YaraScan <mod-yara>`     Scans the sample with Yara and returns the results.
=============================  ========================================

Configuration Options
---------------------

General
^^^^^^^
- **path** - This is where the executable is located.
- **cmdline** - This is an array of command line options be to passed to the executable.
- **host** - This is the hostname, port, and username of the machine that will be SSHed into to run the analytic if the executable is not present on the local machine.
- **key** - This is the SSH key to be used to SSH into the host.
- **replacement path** - If the main config is set to copy the scanned files this will be what it replaces the path with. It should be where the network share is mounted.
- **ENABLED** - When set to false the module will not run.

[main]
^^^^^^
This is the configuration for the main script

- **copyfilesto** - This is where the script will copy each file that is to be scanned. This can be removed or set to False to disable this feature.
- **group-types** - This is the type of analytics to group into sections for the report. This can be removed or set to False to disable this feature.

.. _mod-avg-2014:

[AVGScan]
^^^^^^^^^
This module scans a file with AVG 2014 anti-virus.

.. _mod-clamav:

[ClamAVScan]
^^^^^^^^^^^^
This module scans a file with ClamAV.

.. _mod-cuckoo:

[Cuckoo]
^^^^^^^^
This module submits a file to a Cuckoo Sandbox cluster for analysis.

- **API URL** - This is the URL to the API server
- **timeout** - This is max time a sample with run for
- **running timeout** - This is an additional timeout, if a task is in the running state this many seconds past **timeout** we will consider the task failed.
- **delete tasks** - When set to True, tasks will be deleted from cuckoo after detonation. This is to prevent filling up the Cuckoo machine's disk with reports.
- **maec** - When set to True, `MAEC <https://maecproject.github.io>`_ JSON report is added to Cuckoo JSON report. *NOTE*: Cuckoo needs MAEC reporting enabled to produce results.

.. _mod-exiftools:

[ExifToolsScan]
^^^^^^^^^^^^^^^
This module scans the file with Exif tools and returns the results.

- **remove-entry** - A python list of ExifTool results that should not be included in the report. File system level attributes are not useful and stripped out.

.. _mod-fireeye:

[FireeyeScan]
^^^^^^^^^^^^^
This module uses a FireEye AX to scan the files. It uses the Malware Repository feature to automatically scan files. This may not be the best way but it does work. It will copy the files to be scanned to the mounted share folders.
*NOTE*: This module is suuuuuper slow

- **base path** - The mount point where the fireeye images folders are
- **src folder** - The folder name where input files are put
- **fireeye images** - A python list of the VMs in fireeye. These are used to generate where to copy the files.
- **enabled** - True or False
- **good path** - The folder name where good files are put
- **cheatsheet** - Not implemented yet

.. _mod-floss:

[floss]
^^^^^^^^^^^^
This module extracts ASCII, UTF-8, stack and obfuscated strings from executable files. More information about module configuration can be found at the `flare-floss <https://github.com/fireeye/flare-floss/blob/master/doc/usage.md>`_ documentation.

.. _mod-impfuzzy:

[impfuzzy]
^^^^^^^^^^
This module calculates a fuzzy hash using ssdeep where Windows PE imports is the input. This strategy was originally described in a `blog post <http://blog.jpcert.or.jp/2016/05/classifying-mal-a988.html>`_ from JPCERT/CC.

.. _mod-libmagic:

[libmagic]
^^^^^^^^^^
This module runs libmagic against the files.

- **magicfile** - The path to the compiled magic file you wish to use. If None it will use the default one.

.. _mod-md5:

[MD5]
^^^^^
This module generates the MD5 hash of the files.

.. _mod-mcafee:

[McAfeeScan]
^^^^^^^^^^^^
This module scans the files with McAfee AntiVirus Command Line.

.. _mod-officemeta:

[officemeta]
^^^^^^^^^^^^
This module extracts metadata from Microsoft Office documents.

*Note*: This module does not support `OOXML <https://en.wikipedia.org/wiki/Office_Open_XML>`_ documents (e.g., docx, pptx, xlsx).

.. _mod-pdfinfo:

[pdfinfo]
^^^^^^^^^
This module extracts out feature information from PDF files. It uses `pdf-parser <http://blog.didierstevens.com/programs/pdf-tools/>`_.

.. _mod-pefile:

[PEFile]
^^^^^^^^
This module extracts out feature information from EXE files. It uses `pefile <https://code.google.com/p/pefile/>`_ which is currently not available for python 3.

.. _mod-sha256:

[SHA256]
^^^^^^^^
This module generates the SHA256 hash of the files.

.. _mod-ssdeeper:

[ssdeeper]
^^^^^^^^^^
This module generates context triggered piecewise hashes (CTPH) for the files. More information can be found on the `ssdeep website <http://ssdeep.sourceforge.net/>`_.

.. _mod-tika:

[Tika]
^^^^^^
This module extracts metadata from the file using `Tika <https://tika.apache.org/>`_. For configuration of the module see the `tika-python <https://github.com/chrismattmann/tika-python/blob/master/README.md>`_ documentation.

- **remove-entry** - A python list of Tika results that should not be included in the report.

.. _mod-trid:

[TrID]
^^^^^^
This module runs `TrID <http://mark0.net/soft-trid-e.html>`_ against the files. The definition file should be in the same folder as the executable.

.. _mod-vtsearch:

[vtsearch]
^^^^^^^^^^
This module searches `virustotal <https://www.virustotal.com/>`_ for the files hash and download the report if available.

- **apikey** - This is your public/private api key. You can optionally make it a list and the requests will be distributed across them. This is useful when two groups with private api keys want to share the load and reports.

.. _mod-vxstream:

[VxStream]
^^^^^^^^^^
This module submits a file to a VxStream Sandbox cluster for analysis.

- **API URL** - This is the URL to the API server (include the /api/ in this URL).
- **API Key** - This is the user's API key to the API server.
- **API Secret** - This is the user's secret to the API server.
- **timeout** - This is max time a sample with run for.
- **running timeout** - This is an additional timeout, if a task is in the running state this many seconds past **timeout** we will consider the task failed.

.. _mod-yara:

[YaraScan]
^^^^^^^^^^
This module scans the files with yara and returns the results. You will need yara-python installed for this module.

- **ruledir** - The directory to look for rule files in.
- **fileextensions** - A python array of all valid rule file extensions. Files not ending in one of these will be ignored.
- **ignore-tags** - A python array of yara rule tags that will not be included in the report.
