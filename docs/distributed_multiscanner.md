# Distributed MultiScanner #
MultiScanner now supports a distributed workflow for sample storage, analysis, and report viewing. This new addition includes a web interface, a REST API, a distributed file system (GlusterFS), distributed report storage / searching (ElasticSearch), and task management (Celery / RabbitMQ).

This is what the architecture looks like:

![alt text](https://raw.githubusercontent.com/awest1339/multiscanner/celery/docs/distributed_ms_diagram.PNG)

## Setup ##
Currently, we deploy this system with Ansible. More information about that process can be found here: https://github.com/mitre/multiscanner-ansible. We are also currently working on supporting deploying the distributed architecture via Docker. If you wish to get an idea of how the system works without having to go through the full process of setting up the distributed architecture, look into our docker containers for a standalone system: https://github.com/awest1339/multiscanner/blob/celery/docs/docker_standalone.md. Obviously, the standalone system will be far less scalable / robust / feature rich. However, it will stand up the web UI, the REST API, and an ElasticSearch node for you to see how the system works.
