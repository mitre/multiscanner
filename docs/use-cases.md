MultiScanner is intended to be used by secure operation centers (SOCs), malware analysis centers, and other organization involved with cyber threat information (CTI) sharing. This section outlines associated use cases.  

##Scalable Malware Analysis
Every component of MultiScanner is designed with scaling in mind. 

However, scaling required for external analysis tools such as Cuckoo Sandbox is beyond the scope of MultiScanner code, as is auto-scaling (e.g., scaling required to auto-provision virtual machines). New worker nodes must be deployed manually and added to the Ansible playbook for proper configuration (see [Installing Analytic Machines](install.md#installing-analytic-machines)).

##Manual Malware Analysis
Manual malware analysis is supported via modules.

##Analysis-Oriented Malware Repository
Long term storage of binaries and metadata.

##Data Enrichment
Malware analysis results can be enriched it in support of cyber threat intelligence (CTI) sharing objectives. In addition to analysis of submitted samples, other CTI sources can be integrated with MultiScanner – e.g., TAXII feeds, CTI providers (FireEye, Proofpoint, CrowdStrike, etc.), closed source intel.

##Data Analytics
Analytics can be performed on malware samples either by interacting with the Elasticsearch datastore or via the web/REST UI. 
Two clustering analytics are currently available:

* ssdeep

* *pehash (available yet?)*
