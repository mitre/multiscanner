.. _writing-a-storage-module:

Writing a Storage Module
========================

Each storage object is a class which needs to be derived from ``storage.Storage``. You can have more than one storage object per python file.

Required components
-------------------
You will need to override ``store(self, results)``. ``results`` is a python dictionary that is one of two formats. It is either:

.. code-block:: json

   {
     "Files": {
       "file1": {},
       "file2": {}
     }
     "Metadata": {
       "module1": {},
       "module2": {}
     }
   }

or

.. code-block:: json

   {
     "file1": {},
     "file2": {}
   }

A storage module should support both, even if the metadata is discarded.

Optional components
-------------------

- You can override ``DEFAULTCONF`` in your storage module. This is a dictionary of config options which will appear in the storage config file.
- You can override ``setup(self)``. This should be anything that can be done once to prepare for mutliple calls to ``store``, e.g. opening a network connection or file handle.
- You can override ``teardown(self)``. This will be called when no more ``store`` calls are going to be made.
