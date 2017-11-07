# Standalone Docker Container Notes #
In order to introduce new users to the power of the MultiScanner framework, web UI, and REST API, we have built a standalone docker application that is simple to run in new environments. Simply clone the top level directory and run:
```
$ docker-compose up
```
This will build the 3 necessary containers (one for the web application, one for the REST API, and one for the ElasticSearch backend).

**It is important to note that this is not designed for production use. This is simply a primer for using MultiScanner's web interface. Users should not run this in production or at scale. The MultiScanner framework is highly scalable and distributed, but that doing a full install.**

**Additionally, if you are installing this system behind a proxy, you must edit Dockerfiles in the docker_utils directory. Set line 7 and 8 of https://github.com/awest1339/multiscanner/blob/docker/docker_utils/Dockerfile_api#L7 and https://github.com/awest1339/multiscanner/blob/docker/docker_utils/Dockerfile_web#L7 to the appropriate values for your environment.**
