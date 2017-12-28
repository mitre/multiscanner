.. _analysis-modules:

Analysis Modules
================

The analysis modules currently available in MultiScanner are listed by catagory below.

.. tabularcolumns:: |p{4cm}|p{11cm}|

=============================  ========================================
AV Scans
=============================  ========================================
AVG 2014                       Scans sample with AVG 2014
ClamAVScan                     Scans sample with ClamAV
McAfeeScan                     Scans sample with McAfee AntiVirus Command Line
Microsoft Security Essentials  Scans sample with Microsoft Security Essentials
Metadefender                   Interacts with OPSWAT Metadefender Core 4 Version 3.x, polling Metadefender for scan results.
vtsearch                       Searches VirusTotal for sample’s hash and downloads the report if available               
=============================  ========================================

.. tabularcolumns:: |p{4cm}|p{11cm}|

=============================  ========================================
Sandbox Detonation 
=============================  ========================================
Cuckoo Sandbox                 Submits a sample to Cuckoo Sandbox cluster for analysis.
FireEye API                    Detonates the sample in FireEye AX via FireEye's API.
VxStream                       Submits a file to a VxStream Sandbox cluster for analysis.
=============================  ========================================

.. tabularcolumns:: |p{3cm}|p{12cm}|

=============================  ========================================
Metadata
=============================  ========================================
ExifToolsScan                  Scans sample with Exif tools and returns the results.
MD5                            Generates the MD5 hash of the sample.
PEFile                         Extracts features from EXE files.
SHA1                           Generates the SHA1 hash of the sample.
SHA256                         Generates the SHA256 hash of the sample.
Tika                           Extracts metadata from the sample using `Tika <https://tika.apache.org/)>`_.
TrID                           Runs `TrID <http://mark0.net/soft-trid-e.html)>`_ against a file.
Flare FLOSS                    FireEye Labs Obfuscated String Solver uses static analysis techniques to deobfuscate strings from malware binaries. [floss]|
libmagic                       Runs libmagic against the files to identify filetype.
Metadefender                   Runs Metadefender against a file.
pdfinfo                        Extracts feature information from PDF files using `pdf-parser <http://blog.didierstevens.com/programs/pdf-tools/>`_.
pehasher                       Computes pehash values using a variety of algorithms: totalhase, anymaster, anymaster_v1_0_1, endgame, crits, and pehashng.|
ssdeep                         Generates context triggered piecewise hashes (CTPH) for files. More information can be found on the `ssdeep website <http://ssdeep.sourceforge.net/>`_.
=============================  ========================================

.. tabularcolumns:: |p{3cm}|p{12cm}|

=============================  ========================================
Signatures 
=============================  ========================================
YaraScan                       Scans the sample with Yara and returns the results.
=============================  ========================================