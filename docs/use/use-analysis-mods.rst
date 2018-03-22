.. _analysis-modules:

Analysis Modules
================

The analysis modules currently available in MultiScanner are listed by catagory below.

.. tabularcolumns:: |p{4cm}|p{11cm}|

=================================  ========================================
AV Scans
=================================  ========================================
AVG 2014                           Scans sample with AVG 2014 anti-virus
ClamAVScan                         Scans sample with ClamAV
McAfeeScan                         Scans sample with McAfee AntiVirus Command Line
Microsoft Security Essentials      Scans sample with Microsoft Security Essentials
:ref:`Metadefender <mod-metadef>`  Interacts with OPSWAT Metadefender Core 4 Version 3.x, polling Metadefender for scan results.
:ref:`vtsearch <mod-vtsearch>`     Searches VirusTotal for sample’s hash and downloads the report if available
VFind                              Runs the CyberSoft VFind anti-malware scanner, part of the `VFind Security Toolkit <https://www.cybersoft.com/products/vstk/>`_.
=================================  ========================================

.. tabularcolumns:: |p{3cm}|p{12cm}|

=============================  ========================================
Database
=============================  ========================================
:ref:`NSRL <mod-nsrl>`         Looks up a hash in the `National Software Reference Library <https://www.nist.gov/software-quality-group/national-software-reference-library-nsrl>`_.
=============================  ========================================

.. tabularcolumns:: |p{4cm}|p{11cm}|

===================================  ========================================
Sandbox Detonation
===================================  ========================================
:ref:`Cuckoo Sandbox <mod-cuckoo>`   Submits a sample to Cuckoo Sandbox cluster for analysis.
:ref:`FireEye API <mod-fireeye>`     Detonates the sample in FireEye AX via FireEye's API.
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
MD5                                   Generates the MD5 hash of the sample.
:ref:`officemeta <mod-officemeta>`    Extracts metadata from Microsoft Office documents.
:ref:`pdfinfo <mod-pdfinfo>`          Extracts feature information from PDF files using `pdf-parser <http://blog.didierstevens.com/programs/pdf-tools/>`_.
:ref:`PEFile <mod-pefile>`            Extracts features from EXE files.
pehasher                              Computes pehash values using a variety of algorithms: totalhase, anymaster, anymaster_v1_0_1, endgame, crits, and pehashng.|
SHA1                                  Generates the SHA1 hash of the sample.
SHA256                                Generates the SHA256 hash of the sample.
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

Parameters common to all modules are listed in the next section, followed by notes and module-specific parameters for those that have them.

Common Parameters
^^^^^^^^^^^^^^^^^

The parameters below may be used by all modules.

.. tabularcolumns:: |p{3cm}|p{12cm}|

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

.. _mod-cuckoo:

[Cuckoo]
^^^^^^^^
This module submits a file to a Cuckoo Sandbox cluster for analysis.

.. tabularcolumns:: |p{3cm}|p{12cm}|

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

.. _mod-exiftools:

[ExifToolsScan]
^^^^^^^^^^^^^^^
This module scans the file with Exif tools and returns the results.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
**remove-entry**        A Python list of ExifTool results that should not be included in the report. File system level attributes are not useful and stripped out.
====================  =============================

.. _mod-fireeye:

[FireEyeAPI]
^^^^^^^^^^^^^
This module detonates the sample in FireEye AX via FireEye's API. This "API" version replaces the "FireEye Scan" module.

.. tabularcolumns:: |p{3cm}|p{12cm}|

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

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
**magicfile**           The path to the compiled magic file you wish to use. If None it will use the default one.
====================  =============================

.. _mod-metadef:

[Metadefender]
^^^^^^^^^^^^^^

This module runs Metadefender against the files.

.. tabularcolumns:: |p{3cm}|p{12cm}|

=======================  =============================
Parameter                Description
=======================  =============================
**timeout**               The maximum time a sample will run.
**running timeout**       An additional timeout, if a task is in the running state this many seconds past ``timeout``, the task is considered failed.
**fetch delay seconds**   The number of seconds for the module to wait between submitting all samples and polling for scan results. Increase this value if Metadefender is taking a long time to store the samples.
**poll interval**         The number of seconds between successive queries to Metadefender for scan results. Default is 5 seconds.
**user agent**            Metadefender user agent string, refer to your Metadefender server configuration for this value. Default is "user agent".
=======================  =============================

.. _mod-nsrl:

[NSRL]
^^^^^^

This module looks up hashes in the NSRL database. These two parameters are automatically generated. Users must run nsrl_parse.py tool in the utils/ directory before using this module.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
**hash_list**           The path to the NSRL database on the local filesystem, containing the MD5 hash, SHA1 hash, and original file name.
**offsets**             A file that contains the pointers into hash_list file. This is necessary to speed up searching of the NSRL database file.
====================  =============================

.. _mod-officemeta:

[officemeta]
^^^^^^^^^^^^
This module extracts metadata from Microsoft Office documents.

**Note**: This module does not support `OOXML <https://en.wikipedia.org/wiki/Office_Open_XML>`_ documents (e.g., docx, pptx, xlsx).

.. _mod-pdfinfo:

[pdfinfo]
^^^^^^^^^
This module extracts out feature information from PDF files. It uses `pdf-parser <http://blog.didierstevens.com/programs/pdf-tools/>`_.

.. _mod-pefile:

[PEFile]
^^^^^^^^
This module extracts out feature information from EXE files. It uses `pefile <https://code.google.com/p/pefile/>`_ which is currently not available for python 3.

.. _mod-ssdeeper:

[ssdeeper]
^^^^^^^^^^
This module generates context triggered piecewise hashes (CTPH) for the files. More information can be found on the `ssdeep website <http://ssdeep.sourceforge.net/>`_.

.. _mod-tika:

[Tika]
^^^^^^
This module extracts metadata from the file using `Tika <https://tika.apache.org/>`_. For configuration of the module see the `tika-python <https://github.com/chrismattmann/tika-python/blob/master/README.md>`_ documentation.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
**remove-entry**        A Python list of Tika results that should not be included in the report.
====================  =============================

.. _mod-trid:

[TrID]
^^^^^^
This module runs `TrID <http://mark0.net/soft-trid-e.html>`_ against the files. The definition file should be in the same folder as the executable.

.. _mod-vtsearch:

[vtsearch]
^^^^^^^^^^
This module searches `virustotal <https://www.virustotal.com/>`_ for the files hash and download the report if available.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
**apikey**              Public/private api key. Can optionally make it a list and the requests will be distributed across them. This is useful when two groups with private api keys want to share the load and reports.
====================  =============================

.. _mod-vxstream:

[VxStream]
^^^^^^^^^^
This module submits a file to a VxStream Sandbox cluster for analysis.

.. tabularcolumns:: |p{3cm}|p{12cm}|

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

.. _mod-yara:

[YaraScan]
^^^^^^^^^^
This module scans the files with yara and returns the results. You will need yara-python installed for this module.

.. tabularcolumns:: |p{3cm}|p{12cm}|

====================  =============================
Parameter             Description
====================  =============================
**ruledir**             The directory to look for rule files in.
**fileextensions**      A Python array of all valid rule file extensions. Files not ending in one of these will be ignored.
**ignore-tags**         A Python array of yara rule tags that will not be included in the report.
====================  =============================
