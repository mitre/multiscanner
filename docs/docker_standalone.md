# Standalone Docker Container Notes #
In order to introduce new users to the power of the MultiScanner framework, web UI, and REST API, we have built a standalone docker application that is simple to run in new environments. Simply clone the top level directory and run:
```
$ docker-compose up
```
This will build the 3 necessary containers (one for the web application, one for the REST API, and one for the ElasticSearch backend).

**_Note 1_: We are assuming that you are already running docker and have docker-compose installed on your machine. Guides on how to do that are here: https://docs.docker.com/engine/installation/ and here: https://docs.docker.com/compose/install/**

**_Note 2_: Since this docker container runs two web applications and an ElasticSearch node, there is a fairly high requirement for RAM / computing power. We'd recommend running this on a machine with at least 4GB of RAM.**

**_Note 3_: It is important to note that this is not designed for production use. This is simply a primer for using MultiScanner's web interface. Users should not run this in production or at scale. The MultiScanner framework is highly scalable and distributed, but that doing a full install.**

**_Note 4_: Additionally, if you are installing this system behind a proxy, you must edit Dockerfiles in the docker_utils directory. Set line 7 and 8 of https://github.com/awest1339/multiscanner/blob/docker/docker_utils/Dockerfile_api#L7 and https://github.com/awest1339/multiscanner/blob/docker/docker_utils/Dockerfile_web#L7 to the appropriate values for your environment.**
