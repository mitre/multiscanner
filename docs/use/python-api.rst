.. _python-api:

Python API
==========

Via its RESTful API, MultiScanner can be incorporated as a module in another project. Below is a simple example of how to import MultiScanner into a Python script.

.. code-block:: python

   import multiscanner
   output = multiscanner.multiscan(FileList)
   Results = multiscanner.parse_reports(output, python=True)

``Results`` is a dictionary object where each key is a filename of a scanned file.

``multiscanner.config_init(filepath)`` will create a default configuration file at the location defined by *filepath*.
