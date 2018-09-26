MultiScanner
============
[![Build Status](https://travis-ci.org/mitre/multiscanner.svg)](https://travis-ci.org/mitre/multiscanner)

Introduction
------------
MultiScanner is a file analysis framework that assists the user in evaluating a set
of files by automatically running a suite of tools for the user and aggregating the output.
Tools can be custom built Python scripts, web APIs, software running on another machine, etc.
Tools are incorporated by creating modules that run in the MultiScanner framework.

Modules are designed to be quickly written and easily incorporated into the framework.
Currently written and maintained modules are related to malware analytics, but the framework is not limited to that
scope. For a list of modules you can look in [modules/](modules). Descriptions and config
options can be found on the [Analysis Modules](http://multiscanner.readthedocs.io/en/latest/use/use-analysis-mods.html) page.

MultiScanner also supports a distributed workflow for sample storage, analysis, and
report viewing. This functionality includes a web interface, a REST API, a distributed
file system (GlusterFS), distributed report storage / searching (Elasticsearch), and
distributed task management (Celery / RabbitMQ). Please see [Architecture](http://multiscanner.readthedocs.io/en/latest/arch.html) for more details.

Usage
-----

MultiScanner can be used as a command-line interface, a Python API, or a
distributed system with a web interface. See the documentation for more detailed
information on [installation](http://multiscanner.readthedocs.io/en/latest/install.html) and [usage](http://multiscanner.readthedocs.io/en/latest/use/index.html).

### Command-Line ###

Install Python (2.7 or 3.4+) if you haven't already.

Then run the following (substituting the actual file you want to scan for `<file>`):

``` bash
$ git clone https://github.com/mitre/multiscanner.git
$ cd multiscanner
$ sudo -HE ./install.sh
$ multiscanner init
```

This will generate a default configuration for you. Check `config.ini` to see what
modules are enabled. See [Configuration](http://multiscanner.readthedocs.io/en/latest/install.html#configuration) for more information.

Now you can scan a file (substituting the actual file you want to scan for `<file>`):

``` bash
$ multiscanner <file>
```

You can run the following to get a list of all of MultiScanner's command-line options:

``` bash
$ multiscanner --help
```

**Note**: If you are not on a RedHat or Debian based Linux distribution, instead of
running the `install.sh` script, install pip (if you haven't already) and run the
following:

``` bash
$ pip install -r requirements.txt
```

### Python API ###

``` python
import multiscanner
multiscanner.config_init(filepath)
output = multiscanner.multiscan(file_list)
results = multiscanner.parse_reports(output, python=True)
```

### Web Interface ###

Install the latest versions of [Docker](https://docs.docker.com/engine/installation/)
and [Docker Compose](https://docs.docker.com/compose/install/) if you haven't already.

``` bash
$ git clone https://github.com/mitre/multiscanner.git
$ cd multiscanner
$ docker-compose up
```

You may have to wait a while until all the services are up and running, but then you
can use the web interface by going to `http://localhost:8000` in your web browser.

*Note*: this should not be used in production; it is simply an introduction to what a
full installation would look like. See [here](http://multiscanner.readthedocs.io/en/latest/install.html#standalone-docker-installation) for more details.

Documentation
-------------
For more information, see the [full documentation](http://multiscanner.readthedocs.io/) on ReadTheDocs.
