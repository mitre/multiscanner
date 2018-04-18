Overview
========
MultiScanner is a distributed file analysis framework that assists the user in evaluating a set
of files by automatically running a suite of tools and aggregating the output.
Tools can be custom Python scripts, web APIs, software running on another machine, etc.
Tools are incorporated by creating modules that run in the MultiScanner framework.

By design, modules can be quickly written and easily incorporated into the framework.
While current modules are related to malware analysis, the MultiScanner framework is not limited in
scope. For descriptions of current modules, see :ref:`analysis-modules`.

MultiScanner supports a distributed workflow for sample storage, analysis, and report viewing. This functionality includes a web interface, a REST API, a distributed file system (GlusterFS), distributed report storage / searching (Elasticsearch), and distributed task management (Celery / RabbitMQ). See the :ref:`complete-workflow` section for details.

MultiScanner is available as open source in `GitHub <https://github.com/mitre/multiscanner/tree/feature-celery>`_.

Key Capabilities
----------------
As illustrated in the diagram below, MultiScanner helps the malware analyst, enabling analysis with automated tools and manual tools, providing integration and scaling capabilities, and corrolating analysis results. It allows analysts to associate metadata with samples and also allows integration of data from external sources. MultiScanner is particularly useful because data is linked across tools and samples, allowing pivoting and analytics.

.. figure:: _static/img/overview.png
   :align: center
   :scale: 40 %
   :alt: Overview

   Key Capabilities
