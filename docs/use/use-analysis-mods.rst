.. _analysis-modules:

Analysis Modules
================

The analysis modules currently available in MultiScanner are listed by catagory below.


=================================  ========================================
AV Scans
=================================  ========================================
AVG 2014                           Scans sample with AVG 2014 anti-virus
ClamAVScan                         Scans sample with ClamAV
McAfeeScan                         Scans sample with McAfee AntiVirus Command Line
Microsoft Security Essentials      Scans sample with Microsoft Security Essentials
`Metadefender <#metadefender>`__   Interacts with OPSWAT Metadefender Core 4 Version 3.x, polling Metadefender for scan results.
`vtsearch <#vtsearch>`__           Searches VirusTotal for sample’s hash and downloads the report if available
VFind                              Runs the CyberSoft VFind anti-malware scanner, part of the `VFind Security Toolkit <https://www.cybersoft.com/products/vstk/>`_.
=================================  ========================================


=============================  ========================================
Database
=============================  ========================================
`NSRL <#nsrl>`__               Looks up a hash in the `National Software Reference Library <https://www.nist.gov/software-quality-group/national-software-reference-library-nsrl>`_.
=============================  ========================================


===================================  ========================================
Sandbox Detonation
===================================  ========================================
`Cuckoo Sandbox <#cuckoo>`__         Submits a sample to Cuckoo Sandbox cluster for analysis.
`FireEye API <#fireeyeapi>`__        Detonates the sample in FireEye AX via FireEye's API.
`VxStream <#vxstream>`__             Submits a file to a VxStream Sandbox cluster for analysis.
===================================  ========================================


=============================  ========================================
Machine Learning
=============================  ========================================
MaliciousMacroBot              Triage office files with `MaliciousMacroBot <https://github.com/egaus/MaliciousMacroBot>`_.
=============================  ========================================


====================================  ========================================
Metadata
====================================  ========================================
entropy                               Calculates the Shannon entropy of a file.
`ExifToolsScan <#exiftoolsscan>`__    Scans sample with Exif tools and returns the results.
fileextensions                        Determines possible file extensions for a file.
`floss <#floss>`__                    FireEye Labs Obfuscated String Solver uses static analysis techniques to deobfuscate strings from malware binaries.
`impfuzzy <#impfuzzy>`__              Calculates a fuzzy hash using impfuzzy on Windows PE imports.
`libmagic <#libmagic>`__              Runs libmagic against the files to identify filetype.
MD5                                   Generates the MD5 hash of the sample.
`officemeta <#officemeta>`__          Extracts metadata from Microsoft Office documents.
`pdfinfo <#pdfinfo>`__                Extracts feature information from PDF files using `pdf-parser <http://blog.didierstevens.com/programs/pdf-tools/>`_.
`PEFile <#pefile>`__                  Extracts features from EXE files.
pehasher                              Computes pehash values using a variety of algorithms: totalhase, anymaster, anymaster_v1_0_1, endgame, crits, and pehashng.
SHA1                                  Generates the SHA1 hash of the sample.
SHA256                                Generates the SHA256 hash of the sample.
`ssdeep <#ssdeeper>`__                Generates context triggered piecewise hashes (CTPH) for files. More information can be found on the `ssdeep website <http://ssdeep.sourceforge.net/>`_.
`Tika <#tika>`__                      Extracts metadata from the sample using `Tika <https://tika.apache.org/>`__.
`TrID <#trid>`__                      Runs `TrID <http://mark0.net/soft-trid-e.html>`__ against a file.
UAD                                   Runs the CyberSoft Universal Atomic Disintegrator (UAD) tool, part of the `VFind Security Toolkit <https://www.cybersoft.com/products/vstk/>`_.
====================================  ========================================


=============================  ========================================
Signatures
=============================  ========================================
`YaraScan <#yarascan>`__       Scans the sample with Yara and returns the results.
=============================  ========================================

Configuration Options
---------------------

Parameters common to all modules are listed in the next section, followed by notes and module-specific parameters for those that have them.

Common Parameters
^^^^^^^^^^^^^^^^^

The parameters below may be used by all modules.

====================  =============================
Parameter             Description
====================  =============================
**path**                Location of the executable.
**cmdline**             An array of command line options to be passed to the executable.
**host**                The hostname, port, and username of the machine that will be SSH’d into to run the analytic if the executable is not present on the local machine.
**key**                 The SSH key to be used to SSH into the host.
**replacement path**    If the main config is set to copy the scanned files this will be what it replaces the path with. It should be where the network share is mounted.
**ENABLED**             When set to false, the module will not run.
====================  =============================

[Cuckoo]
^^^^^^^^
This module submits a file to a Cuckoo Sandbox cluster for analysis.

====================  =============================
Parameter             Description
====================  =============================
**API URL**             The URL to the API server.
**WEB URL**             The URL to the Web server.
**timeout**             The maximum time a sample will run.
**running timeout**     An additional timeout, if a task is in the running state this many seconds past ``timeout``, the task is considered failed.
**delete tasks**        When set to True, tasks will be deleted from Cuckoo after detonation. This is to prevent filling up the Cuckoo machine's disk with reports.
**maec**                When set to True, a `MAEC <https://maecproject.github.io>`_ JSON-based report is added to Cuckoo JSON report. **NOTE**: Cuckoo needs MAEC reporting enabled to produce results.
====================  =============================

[ExifToolsScan]
^^^^^^^^^^^^^^^
This module scans the file with Exif tools and returns the results.

====================  =============================
Parameter             Description
====================  =============================
**remove-entry**        A Python list of ExifTool results that should not be included in the report. File system level attributes are not useful and stripped out.
====================  =============================

[FireEyeAPI]
^^^^^^^^^^^^^
This module detonates the sample in FireEye AX via FireEye's API. This "API" version replaces the "FireEye Scan" module.

====================  =============================
Parameter             Description
====================  =============================
**API URL**             The URL to the API server.
**fireeye images**      A Python list of the VMs in fireeye. These are used to generate where to copy the files.
**username**            Username on the FireEye AX.
**password**            Password for the FireEye AX.
**info level**          Options are concise, normal, and extended.
**timeout**             The maximum time a sample will run.
**force**               If set to True, will rescan if the sample matches a previous scan.
**analysis type**       0 = sandbox, 1 = live.
**application id**      For AX Series appliances (7.7 and higher) and CM Series appliances that manage AX Series appliances (7.7 and higher), setting the application value to -1 allows the AX Series appliance to choose the application. For other appliances, setting the application value to 0 allows the AX Series appliance to choose the application.
====================  =============================

[floss]
^^^^^^^
This module extracts ASCII, UTF-8, stack and obfuscated strings from executable files. More information about module configuration can be found at the `flare-floss <https://github.com/fireeye/flare-floss/blob/master/doc/usage.md>`_ documentation.

[impfuzzy]
^^^^^^^^^^
This module calculates a fuzzy hash using ssdeep where Windows PE imports is the input. This strategy was originally described in a `blog post <http://blog.jpcert.or.jp/2016/05/classifying-mal-a988.html>`_ from JPCERT/CC.

[libmagic]
^^^^^^^^^^
This module runs libmagic against the files.

====================  =============================
Parameter             Description
====================  =============================
**magicfile**           The path to the compiled magic file you wish to use. If None it will use the default one.
====================  =============================

[Metadefender]
^^^^^^^^^^^^^^

This module runs Metadefender against the files.

=======================  =============================
Parameter                Description
=======================  =============================
**timeout**               The maximum time a sample will run.
**running timeout**       An additional timeout, if a task is in the running state this many seconds past ``timeout``, the task is considered failed.
**fetch delay seconds**   The number of seconds for the module to wait between submitting all samples and polling for scan results. Increase this value if Metadefender is taking a long time to store the samples.
**poll interval**         The number of seconds between successive queries to Metadefender for scan results. Default is 5 seconds.
**user agent**            Metadefender user agent string, refer to your Metadefender server configuration for this value. Default is "user agent".
=======================  =============================

[NSRL]
^^^^^^

This module looks up hashes in the NSRL database. These two parameters are automatically generated. Users must run nsrl_parse.py tool in the utils/ directory before using this module.

====================  =============================
Parameter             Description
====================  =============================
**hash_list**           The path to the NSRL database on the local filesystem, containing the MD5 hash, SHA1 hash, and original file name.
**offsets**             A file that contains the pointers into hash_list file. This is necessary to speed up searching of the NSRL database file.
====================  =============================

[officemeta]
^^^^^^^^^^^^
This module extracts metadata from Microsoft Office documents.

**Note**: This module does not support `OOXML <https://en.wikipedia.org/wiki/Office_Open_XML>`_ documents (e.g., docx, pptx, xlsx).

[pdfinfo]
^^^^^^^^^
This module extracts out feature information from PDF files. It uses `pdf-parser <http://blog.didierstevens.com/programs/pdf-tools/>`_.

[PEFile]
^^^^^^^^
This module extracts out feature information from EXE files. It uses `pefile <https://code.google.com/p/pefile/>`_ which is currently not available for python 3.

[ssdeeper]
^^^^^^^^^^
This module generates context triggered piecewise hashes (CTPH) for the files. More information can be found on the `ssdeep website <http://ssdeep.sourceforge.net/>`_.

[Tika]
^^^^^^
This module extracts metadata from the file using `Tika <https://tika.apache.org/>`_. For configuration of the module see the `tika-python <https://github.com/chrismattmann/tika-python/blob/master/README.md>`_ documentation.

====================  =============================
Parameter             Description
====================  =============================
**remove-entry**        A Python list of Tika results that should not be included in the report.
====================  =============================

[TrID]
^^^^^^
This module runs `TrID <http://mark0.net/soft-trid-e.html>`_ against the files. The definition file should be in the same folder as the executable.

[vtsearch]
^^^^^^^^^^
This module searches `virustotal <https://www.virustotal.com/>`_ for the files hash and download the report if available.

====================  =============================
Parameter             Description
====================  =============================
**apikey**              Public/private api key. Can optionally make it a list and the requests will be distributed across them. This is useful when two groups with private api keys want to share the load and reports.
====================  =============================

[VxStream]
^^^^^^^^^^
This module submits a file to a VxStream Sandbox cluster for analysis.

====================  =============================
Parameter             Description
====================  =============================
**BASE URL**            The base URL of the VxStream server.
**API URL**             The URL to the API server (include the /api/ in this URL).
**API Key**             The user's API key to the API server.
**API Secret**          The user's secret to the API server.
**Environment ID**      The environment in which to execute the sample (if you have different sandboxes configured).
**Verify**              Set to false to ignore TLS certificate errors when querying the VxStream server.
**timeout**             The maximum time a sample will run
**running timeout**     An additional timeout, if a task is in the running state this many seconds past ``timeout``, the task is considered failed.
====================  =============================

[YaraScan]
^^^^^^^^^^
This module scans the files with yara and returns the results. You will need yara-python installed for this module.

====================  =============================
Parameter             Description
====================  =============================
**ruledir**             The directory to look for rule files in.
**fileextensions**      A Python array of all valid rule file extensions. Files not ending in one of these will be ignored.
**ignore-tags**         A Python array of yara rule tags that will not be included in the report.
====================  =============================
