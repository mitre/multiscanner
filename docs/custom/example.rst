.. _example:

Example Module
==============

.. code-block:: python

   from __future__ import (division, absolute_import, with_statement,
                           print_function, unicode_literals)

   TYPE = "Example"
   NAME = "include example"
   REQUIRES = ["libmagic", "MD5"]
   DEFAULTCONF = {
       'ENABLED': True,
   }

   def check(conf=DEFAULTCONF):
       # If the config disabled the module don't run
       if not conf['ENABLED']:
           return False
       # If one of the required modules failed, don't run
       if None in REQUIRES:
           return False
       return True


   def scan(filelist, conf=DEFAULTCONF):
       # Define our results array
       results = []
       # Pull out the libmagic results and metadata
       libmagicresults, libmagicmeta = REQUIRES[0]

       # Pull out the md5 results and metadata
       md5results, md5meta = REQUIRES[1]
       # Make the md5 results a dictionary
       md5dict = dict(md5results)

       # Run through each value in the libmagic results
       for filename, libmagicresult in libmagicresults:
           if libmagicresult.startswith('PDF document'):
               # If the file's md5 is present we will use that in the results
               if filename in md5dict:
                   results.append((filename, md5dict[filename] + " is a pdf"))
               # If we don't know the md5 use the filename instead
               else:
                   results.append((filename, "is a pdf"))

       # Create out metadata dictionary
       metadata = {}
       metadata["Name"] = NAME
       metadata["Type"] = TYPE

       # Return our super awesome results
       return (results, metadata)
