Installation
============

Installation information for the different components of MultiScanner is provided below. To get an idea of how the system works without going through the full process of setting up the distributed architecture, refer to the section on :ref:`standalone-docker-installation`.

The Docker standalone system is less scalable, robust, and feature-rich, but it enables easy stand up the web UI, the REST API, and an Elasticsearch node, allowing users to quickly see how the system works. The standalone container is intended as an introduction to the system and its capabilities, but is not designed for operational use.

System Requirements
-------------------

Python 3.6 is recommended. Compatibility with Python 2.7+ and 3.5+ is supported but not thoroughly maintained and tested. Please submit an issue or a pull request fixing any issues found with other versions of Python.

An installer script is included in the project (`install.sh <https://github.com/mitre/multiscanner/blob/feature-celery/install.sh>`_), which installs the prerequisites on most systems.

Currently, MultiScanner is deployed with Ansible, and we're working to support distributed architecture deployment via Docker.

Installing Ansible
------------------

The `installer script <https://github.com/mitre/multiscanner/blob/feature-celery/install.sh>`_ should install the required Python packages for users of RedHat- or Debian-based Linux distributions. Users of other distributions should refer to `requirements.txt <https://github.com/mitre/multiscanner/blob/feature-celery/requirements.txt>`_.

MultiScanner requires a configuration file to run. After cloning the repository, generate the MultiScanner default
configuration by running ``python multiscanner.py init``. The command can be used to rewrite the configuration file to its default state or, if new modules have been written, to add their configuration details to the configuration
file.

.. _installing-analytic-machines:

Installing Analytic Machines
----------------------------

Default modules have the option of being run locally or via SSH. The development team
runs MultiScanner on a Linux host and hosts the majority of analytical tools on
a separate Windows machine. The SSH server used in this environment is `freeSSHd <http://www.freesshd.com/>`_.

A network share accessible to both the MultiScanner and the analytic machines is
required for the multi-machine setup. Once configured, the network share path must
be identified in the configuration file, config.ini (an example can be found
`here <https://github.com/mitre/multiscanner/blob/master/docker_utils/config.ini>`_).
To do this, set the ``copyfilesto`` option under ``[main]`` to be the mount point on the system running MultiScanner.
Modules can have a ``replacement path`` option, which is the network share mount point
on the analytic machine.

Installing Elasticsearch
------------------------

Starting with Elasticsearch 2.x, field names can no longer contain '.' (dot) characters. Thus, the MultiScanner elasticsearch_storage module adds a pipeline called "dedot" with a processor to replace dots in field names with underscores.

Add the following to the elasticsearch.yml configuration file for the dedot processor to work::

    script.painless.regex.enabled: true


To use the Multiscanner web UI, also add the following::

    http.cors.enabled: true
    http.cors.allow-origin: "<yourOrigin>"

Configuration
-------------

MultiScanner and its modules are configured within the configuration file, config.ini. An example can be found
`here <https://github.com/mitre/multiscanner/blob/master/docker_utils/config.ini>`_.

The following parameters configure MultiScanner itself, and go in the ``[main]``
section of the config file.

====================  =============================
Parameter             Description
====================  =============================
**copyfilesto**         This is where the script will copy each file that is to be scanned. This can be removed or set to False to disable this feature.
**group-types**         This is the type of analytics to group into sections for the report. This can be removed or set to False to disable this feature.
**storage-config**      Path to the storage config file.
**api-config**          Path to the API config file.
**web-config**          Path to the Web UI config file.
====================  =============================

Modules are intended to be quickly written and incorporated into the framework. Note that:

* A finished module must be placed in the modules folder before it can be used.

* The configuration file does not need to be manually updated.

* Modules are configured within the same configuration file, config.ini.

See :ref:`analysis-modules` for information about all current modules and their configuration parameters.

.. _standalone-docker-installation:

Standalone Docker Installation
------------------------------

To introduce new users to the power of the MultiScanner framework, web UI, and REST API, we have built a standalone docker application that is simple to run in new environments. Simply clone the top level directory and run::

    $ docker-compose up

This will build the three necessary containers (one for the web application, one for the REST API, and one for the Elasticsearch backend).

Running this command will generate a lot of output and take some time. The system is not ready until you see the following output in your terminal::

    api_1      |  * Running on http://0.0.0.0:8080/ (Press CTRL+C to quit)

Now you can go to the web interface at ``http://localhost:8000``.

.. note::

  We are assuming that you are already running latest version of docker and have the latest version of docker-compose installed on your machine. Guides on how to do that are `here <https://docs.docker.com/engine/installation/>`__. and `here <https://docs.docker.com/compose/install/>`__.

.. note::

  Since this docker container runs two web applications and an ElasticSearch node, there is a fairly high requirement for RAM / computing power. We'd recommend running this on a machine with at least 4GB of RAM.

.. warning::

  THIS CONTAINER IS NOT DESIGNED FOR PRODUCTION USE. This is simply a primer for using MultiScanner's web interface. Users should not run this in production or at scale. The MultiScanner framework is highly scalable and distributed, but that requires a full install. Currently, we support installing the distributed system via ansible. More information about that process can be found in `this repo <https://github.com/mitre/multiscanner-ansible>`_.

.. note::

  This container will only be reachable / functioning on localhost.

.. note::

  Additionally, if you are installing this system behind a proxy, you must edit the docker-compose.yml file in four places. First, uncomment `lines 18-20 <../docker-compose.yml#L18>`_ and `lines 35-37 <../docker-compose.yml#L35>`_. Next, uncomment `lines 25-28 <../docker-compose.yml#L25>`_ and set the correct proxy variables there. Finally, do the same thing in `lines 42-45 <../docker-compose.yml#L42>`_. The docker-compose.yml file has comments to make clear where to make these changes.
