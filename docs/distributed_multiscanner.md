# Distributed MultiScanner #
MultiScanner now supports a distributed workflow for sample storage, analysis, and report viewing. This new addition includes a web interface, a REST API, a distributed file system (GlusterFS), distributed report storage / searching (ElasticSearch), and task management (Celery / RabbitMQ).

## Architecture ##
This is what the current architecture looks like:

![alt text](https://raw.githubusercontent.com/awest1339/multiscanner/celery/docs/distributed_ms_diagram.PNG)

When a sample is submitted (either via the web UI or the REST API), the sample is saved to the distributed file system (GlusterFS), a task is added to the distributed task queue (Celery), and an entry is added to the task management database (PostgreSQL). The worker nodes (Celery clients) all have the GlusterFS mounted, which gives them access to the samples for scanning. In our setup, we colocate the worker nodes with the GlusterFS nodes in order to reduce the network load of workers pulling samples from GlusterFS. When a new task is added to the Celery task queue, one of the worker nodes will pull the task and retrieve the corresponding sample from the GlusterFS via its SHA256 value. The worker node then performs the scanning work. For a full list of modules, look here: https://github.com/awest1339/multiscanner/blob/celery/docs/modules.md. Modules can be enabled / disabled via a configuration file. When the worker finishes its scans, it will generate a JSON blob and index that JSON into ElasticSearch for permanent storage / searching. It will then update the task management database with a status of "Complete". The user will then be able view the report via the web interface or retrieve the raw JSON.

## Intended Use case ##
MAF is intended to solve any combination of these problems / use cases:

* Malware repository (i.e, long term storage of binaries and metadata)
* Scalable analysis capabilities
  * Every component of the MAF is designed with scale in mind
  * Note this does not include the following:
    * The scaling of external malware analysis tools such as Cuckoo
    * Does not perform auto-scaling (e.g. auto-provisioning of VM’s, etc)
    * New nodes must be deployed manually and added to the Ansible playbook to receive the proper configurations
* Enable analytics on malware samples
  * Either by interacting with the ElasticSearch backend or plugging into the web / REST UI
  * CTI integration / storage
* Export CTI
  * Intended to output reports in multiple formats: STIX, PDF, HTML, JSON, and text.
  * Allows for export of raw JSON reports
  * Allows for export of MAEC 5.0 reports
  * Sharing malware analysis results
  * Either within the framework’s UI itself or by exporting as JSON and sharing.
* Support file submission types:
  * Currently support all file formats (e.g. PE, PDF, Office, etc…)
  * Currently doesn’t support extraction of files from PCAP / memory dumps / other data streams (but that is in the dev plan)
* Intended users:
  * SOCs
  * Malware analysis centers
  * CTI sharing organizations

## Setup ##
Currently, we deploy this system with Ansible. More information about that process can be found here: https://github.com/mitre/multiscanner-ansible. We are also currently working on supporting deploying the distributed architecture via Docker. If you wish to get an idea of how the system works without having to go through the full process of setting up the distributed architecture, look into our docker containers for a standalone system: https://github.com/awest1339/multiscanner/blob/celery/docs/docker_standalone.md. Obviously, the standalone system will be far less scalable / robust / feature rich. However, it will stand up the web UI, the REST API, and an ElasticSearch node for you to see how the system works.

## Architecture Details ##
What follows is a brief discussion of the tools and design choices we made in the creation of this system.

### Web Frontend ###
The web application is written in Flask, using vanilla JavaScript and jQuery. It is essentially a aesthetic wrapper around the REST API, all data and services are provided by querying the REST API.

### REST API ###
The REST API is also written in Flask. It has an underlying PostgreSQL database in order to facilitate task tracking. Additionally, it acts as a gateway to the backend ElasticSearch document store. 

### Task Queue ###
We use Celery as our distributed task queue. 

### Task Tracking ###
PostgreSQL is our task management database. It is here that we keep track of scan times, samples, and the status of tasks (pending, complete, failed, etc...).

### Distributed File System ###
GlusterFS is our selection for our distributed file system. Each componenet that needs access to the raw samples mounts the share. We selected GlusterFS because it is much more performant in our use case of storing a large number of small samples than a technology like HDFS is.

### Worker Nodes ###
The worker nodes are simply Celery clients running the MultiScanner python application. Addtionally, we implemented some batching within Celery to improve the performance of our worker nodes (which operate better at scale).

### Report Storage ###
We use ElasticSearch to store the results of our file scans. This is where the true power of this system comes in. ElasticSearch allows for performant, full text searching across all our reports and modules. This allows for fast access to interesting details from your malware analysis tools, pivoting between samples, and powerful analytics on report output.
