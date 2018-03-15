Use Cases
=========

MultiScanner is intended to be used by security operations centers, malware analysis centers, and other organizations involved with cyber threat intelligence (CTI) sharing. This section outlines associated use cases.

Scalable Malware Analysis
-------------------------
Every component of MultiScanner is designed with scaling in mind, enabling analysis of large malware data sets.

Note that scaling required for external analysis tools such as Cuckoo Sandbox is beyond the scope of MultiScanner code, as is auto-scaling (e.g., scaling required to auto-provision virtual machines). New worker nodes must be deployed manually and added to the Ansible playbook for proper configuration (see :ref:`installing-analytic-machines`).

Manual Malware Analysis
-------------------------
MultiScanner can support manual malware analysis via modules that enable analyst interaction. For example, a module could be developed to allow an analyst to interact with IDA Pro to disassemble and analyze a binary file.

Analysis-Oriented Malware Repository
------------------------------------
MultiScanner enables long term storage of binaries and metadata associated with malware analysis.

Data Enrichment
---------------
Malware analysis results can be enriched in support of CTI sharing objectives. In addition to data derived from analysis of submitted samples, other CTI sources can be integrated with MultiScanner, such as TAXII feeds, commercial CTI providers (FireEye, Proofpoint, CrowdStrike, etc.), and closed-source CTI providers.

Data Analytics
--------------
Data analytics can be performed on malware samples either by interacting with the Elasticsearch datastore or via the Web/REST UI.
