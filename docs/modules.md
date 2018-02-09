### General ###
- **path** - This is where the executable is located
- **cmdline** - This is an array of command line options be to passed to the executable
- **host** - This is the hostname, port, and username of the machine that will be SSHed into to run the analytic if the executable is not present on the local machine.
- **key** - This is the SSH key to be used to SSH into the host.
- **replacement path** - If the main config is set to copy the scanned files this will be what it replaces the path with. It should be where the network share is mounted
- **ENABLED** - When set to false the module will not run

### [main] ###
This is the configuration for the main script

- **copyfilesto** - This is where the script will copy each file that is to be scanned. This can be removed or set to False to disable this feature
- **group-types** - This is the type of analytics to group into sections for the report. This can be removed or set to False to disable this feature

### [AVGScan] ###
This module scans a file with AVG 2014 anti-virus.

### [ClamAVScan] ###
This module scans a file with ClamAV.

### [Cuckoo] ###
This module submits a file to a Cuckoo Sandbox cluster for analysis

- **API URL** - This is the URL to the API server
- **timeout** - This is max time a sample with run for
- **running timeout** - This is an additional timeout, if a task is in the running state this many seconds past **timeout** we will consider the task failed.
- **delete tasks** - When set to True, tasks will be deleted from cuckoo after detonation. This is to prevent filling up the Cuckoo machine's disk with reports.
- **maec** - When set to True, [MAEC](https://maecproject.github.io) JSON report is added to Cuckoo JSON report. *NOTE*: Cuckoo needs MAEC reporting enabled to produce results.

### [ExifToolsScan] ###
This module scans the file with Exif tools and returns the results.

- **remove-entry** - A python list of ExifTool results that should not be included in the report. File system level attributes are not useful and stripped out 

### [FireeyeScan] ###
This module uses a FireEye AX to scan the files. It uses the Malware Repository feature to automatically scan files. This may not be the best way but it does work. It will copy the files to be scanned to the mounted share folders.
*NOTE*: This module is suuuuuper slow

- **base path** - The mount point where the fireeye images folders are
- **src folder** - The folder name where input files are put
- **fireeye images** - A python list of the VMs in fireeye. These are used to generate where to copy the files.
- **enabled** - True or False
- **good path** - The folder name where good files are put
- **cheatsheet** - Not implemented yet

### [flarefloss] ###
This module extracts ASCII, UTF-8, stack and obfuscated strings from executable files. More information about module configuration can be found at the [flare-floss](https://github.com/fireeye/flare-floss/blob/master/doc/usage.md) documentation.

### [impfuzzy] ###
This module calculates a fuzzy hash using ssdeep where Windows PE imports is the input. This strategy was originally described in a [blog post](http://blog.jpcert.or.jp/2016/05/classifying-mal-a988.html) from JPCERT/CC.

### [libmagic] ###
This module runs libmagic against the files.

- **magicfile** - The path to the compiled magic file you wish to use. If None it will use the default one.

### [MD5] ###
This module generates the MD5 hash of the files.

### [McAfeeScan] ###
This module scans the files with McAfee AntiVirus Command Line.

### [officemeta] ###
This module extracts metadata from Microsoft Office documents.

*Note*: This module does not support [OOXML](https://en.wikipedia.org/wiki/Office_Open_XML) documents (e.g., docx, pptx, xlsx).

### [pdfinfo] ###
This module extracts out feature information from PDF files. It uses [pdf-parser](http://blog.didierstevens.com/programs/pdf-tools/)

### [PEFile] ###
This module extracts out feature information from EXE files. It uses [pefile](https://code.google.com/p/pefile/) which is currently not available for python 3.

### [SHA256] ###
This module generates the SHA256 hash of the files.

### [ssdeeper] ###
This module generates context triggered piecewise hashes (CTPH) for the files. More information can be found on the [ssdeep website](http://ssdeep.sourceforge.net/).

### [Tika] ###
This module extracts metadata from the file using [Tika](https://tika.apache.org/). For configuration of the module see the [tika-python](https://github.com/chrismattmann/tika-python/blob/master/README.md) documentation.

- **remove-entry** - A python list of Tika results that should not be included in the report.

### [TrID] ###
This module runs [TrID](http://mark0.net/soft-trid-e.html) against the files. The definition file should be in the same folder as the executable

### [vtsearch] ###
This module searches [virustotal](https://www.virustotal.com/) for the files hash and download the report if available.

- **apikey** - This is your public/private api key. You can optionally make it a list and the requests will be distributed across them. This is useful when two groups with private api keys want to share the load and reports

### [VxStream] ###
This module submits a file to a VxStream Sandbox cluster for analysis

- **API URL** - This is the URL to the API server (include the /api/ in this URL)
- **API Key** - This is the user's API key to the API server
- **API Secret** - This is the user's secret to the API server
- **timeout** - This is max time a sample with run for
- **running timeout** - This is an additional timeout, if a task is in the running state this many seconds past **timeout** we will consider the task failed.

### [YaraScan] ###
This module scans the files with yara and returns the results. You will need yara-python installed for this module.

- **ruledir** - The directory to look for rule files in
- **fileextensions** - A python array of all valid rule file extensions. Files not ending in one of these will be ignored.
- **ignore-tags** - A python array of yara rule tags that will not be included in the report.
