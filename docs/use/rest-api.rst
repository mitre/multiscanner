RESTful API
===========

The MultiScanner RESTful API is provided by a Flask app that supports accessing submitted samples, and information about tasks, reports, and modules.

Most endpoints prodive a JSON response. The only exceptions are those endpoints that provide downloadable files and documents (e.g., submitted samples, STIX documents, PDFs).

The API endpoints all have Cross Origin Resource Sharing (CORS) enabled. By default it will allow requests from any port on localhost. Change this setting by modifying the ``cors`` setting in the ``api`` section of the API config file.

Download Samples
----------------

Download samples that have been submitted to MultiScanner for analysis.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v2/files/<sha256>?raw={t|f}                    | File download                            |
+--------+-----------------------------------------------------+------------------------------------------+
| Download sample with the specified SHA256 hash. Download defaults to password protected zip; use `raw=t`|
| to download a raw binary instead.                                                                       |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v2/tasks/<task_id>/file?raw={t|f}              | File download                            |
+--------+-----------------------------------------------------+------------------------------------------+
| Download sample associated with the given `task_id`. Download defaults to password protected zip; use   |
| `raw=t` to download a raw binary instead.                                                               |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v2/tasks/files?tasks_ids=<task_ids>            | Zip file download                        |
+--------+-----------------------------------------------------+------------------------------------------+
| Given a comma-separated list of task IDs, receive a protected zip with multiple samples. The password   |
| of the zip archive is ``infected``.                                                                     |
+---------------------------------------------------------------------------------------------------------+


Tasks
-----

View, submit, and search analysis tasks.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v2/tasks                                       | List of `tasks <#task>`_                 |
+--------+-----------------------------------------------------+------------------------------------------+
| Get a list of tasks in MultiScanner                                                                     |
+--------+-----------------------------------------------------+------------------------------------------+
| POST   | /api/v2/tasks                                       | List of task IDs                         |
+--------+-----------------------------------------------------+------------------------------------------+
| Submit file sample via POST file, and receive a task ID for the analysis of the submission.             |
|                                                                                                         |
| Sample POST usage: `curl -i -X POST http://localhost:8080/api/v2/tasks -F file=@/bin/ls`                |
|                                                                                                         |
| Sample response: ``[5, 6, 7]``                                                          |
|                                                                                                         |
| Expects a file in the request body named ``file``, and also admits the following HTTP form keys:        |
|  * ``duplicate`` - either ``rescan`` (do a scan even if this file has been previously submitted)        |
|      or ``latest`` (use the latest scan that has already been done on this file, if one exists)         |
|  * ``archive-analyze`` - set to ``true`` to unpack submission as an archive before analysis             |
|  * ``archive-password`` - password to use when unpacking archive submission, UTF-8 encoded              |
|  * ``upload_type`` - use and set to ``import`` to submit a JSON representation of a MultiScanner task   |
|       downloaded from  ``/api/v2/tasks/<task_id>/report`` instead of a sample file for analysis         |
|  * Any other keys supplied are saved as keys on the task's metadata                                     |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v2/tasks/<task_id>                             | `Task`_                                  |
+--------+-----------------------------------------------------+------------------------------------------+
| Get information about the task with the given `task_id`                                                 |
+--------+-----------------------------------------------------+------------------------------------------+
| DELETE | /api/v2/tasks/<task_id>                             | Confirmation text                        |
+--------+-----------------------------------------------------+------------------------------------------+
| Delete task with the given `task_id`                                                                    |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v2/tasks/datatable                             | List with a single `task`_               |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of most recent report for matching samples. For use with Lucene queries.                   |
| **Intended for use via DataTables integration, not normal API use.**                                    |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v2/tasks/datatable/history                     | List of `tasks <#task>`_                 |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of all reports for matching samples                                                        |
| **Intended for use via DataTables integration, not normal API use.**                                    |
+---------------------------------------------------------------------------------------------------------+

Reporting
---------

View anlysis information gathered by a task in various formats.

+--------+------------------------------------------------------------------------------+-----------------------------------+
| GET    | /api/v2/tasks/<task_id>/report?d={t|f}                                       | Analysis `report`_ in JSON        |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| Receive report in JSON; set ``d=t`` to download or ``d=f`` to view                                                        |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| GET    | /api/v2/tasks/reports?d={t|f}&tasks_ids=<task_ids>                           | List of JSON `reports <#report>`_ |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| Given a comma-separated list of task IDs, receive a list of reports in JSON. Set ``d=t`` to download                      |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| GET    | /api/v2/tasks/<task_id>/pdf                                                  | Human-readable PDF document       |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| Receive PDF report for task                                                                                               |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| GET    | /api/v2/tasks/<task_id>/maec                                                 | MAEC file                         |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| Download the Cuckoo MAEC 5.0 report, if it exists                                                                         |
+--------+-----------------------------------------------------+------------------------+-----------------------------------+
| GET    | /api/v2/tasks/<task_id>/stix2?pretty={t|f}&custom_labels=<labels>            | STIX 2 Bundle                     |
+--------+-----------------------------------------------------+------------------------+-----------------------------------+
| Receive STIX2 Bundle based on the analysis task identified by ID. Also accepts a comma-separated list of ``custom_labels``|
+--------+------------------------------------------------------------------------------+-----------------------------------+
| GET    | /api/v2/tasks/stix2?pretty={t|f}&custom_labels=<labels>&tasks_ids=<task_ids> | List of Stix 2 Bundles            |
+--------+------------------------------------------------------------------------------+-----------------------------------+
| Receive a list of STIX 2 Bundles based the anlysis tasks identified by comma-separated IDs. Also accepts a                |
| comma-separated list of ``custom_labels``                                                                                 |
+---------------------------------------------------------------------------------------------------------------------------+

Tags
----

These endpoints manipulate tags on a report. To view tags on a report, use the ``tasks/<task_id>/report`` endpoint.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v2/tags                                        | List of ``{ key, doc_count }`` objects   |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of all tags in use. Response is a list of objects each with a ``key`` property (the tag)   |
| and ``doc_count`` property (the number of documents in which the tag appears).                          |
+--------+-----------------------------------------------------+------------------------------------------+
| POST   | /api/v2/tasks/<task_id>/tags                        | Confirmation message                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Add a tag to a task. Use HTTP form parameter ``tag``, i.e., ``tag=...`` with                            |
| ``Content-type: application/x-www-form-urlencoded`` header                                              |
+--------+-----------------------------------------------------+------------------------------------------+
| DELETE | /api/v2/tasks/<task_id>/tags                        | Confirmation message                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Remove a tag from a task. Use HTTP form parameter ``tag``, i.e., ``tag=...`` with                       |
+--------+-----------------------------------------------------+------------------------------------------+


Notes
-----

Notes are a way for analyists to add freeform commentary on samples. Notes are associated with a task's sample, so two tasks run on an identical sample share the same set of notes.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v2/tasks/<task_id>/notes                       | List of `notes <#note>`_                 |
+--------+-----------------------------------------------------+------------------------------------------+
| Get a list of notes on this task's sample                                                               |
+--------+-----------------------------------------------------+------------------------------------------+
| POST   | /api/v2/tasks/<task_id>/notes                       | Confirmation message                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Add a note to task, using the HTTP parameter ``text=...``                                               |
+--------+-----------------------------------------------------+------------------------------------------+
| PUT    | /api/v2/tasks/<task_id>/notes/<note_id>             |                                          |
+--------+-----------------------------------------------------+------------------------------------------+
| Edit a notesing the HTTP parameter ``text=...``                                                         |
+--------+-----------------------------------------------------+------------------------------------------+
| DELETE | /api/v2/tasks/<task_id>/notes/<note_id>             | Confirmation message                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Delete a note                                                                                           |
+--------+-----------------------------------------------------+------------------------------------------+


Modules/Other
-------------

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v2/modules                                     | JSON object with module names as keys    |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive an object whose keys are the names of available of modules. The corresponding value of each key |
| is a ``true``/``false`` boolean that indicates whether the module is currently activated or not.        |
+--------+-----------------------------------------------------+------------------------------------------+
|| GET   | /api/v2/analytics/ssdeep_compare                    | Confirmation message                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Run ssdeep.compare analytic                                                                             |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v2/analytics/ssdeep_group                      | List of lists of SHA256 hash strings     |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of sample hashes grouped into lists by ssdeep hash                                         |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /                                                   | Test response object                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Test functionality. Should produce: ``{'Message': 'True'}``                                             |
+---------------------------------------------------------------------------------------------------------+


Data Models
===========

Task
----

A task is a created at the time a sample is submitted. It is a "pending" state while the modules produce an analysis, and then it is in a "completed" state.

Task data is expressed as a JSON object with the following keys:

+-------------+---------+------------------------------------------------------------------------------------------+
| Property    | Type    | Description                                                                              |
+=============+=========+==========================================================================================+
| task_id     | Integer | Unique ID of the task                                                                    |
+-------------+---------+------------------------------------------------------------------------------------------+
| sample_id   | String  | ID of the sample submitted. This will be the same for different tasks with identical     |
|             |         | samples. (Currently, it's a hash of the submitted binary.)                               |
+-------------+---------+------------------------------------------------------------------------------------------+
| task_status | String  | Initially "Pending", and eventually "Completed"                                          |
+-------------+---------+------------------------------------------------------------------------------------------+
| timestamp   | String  | ISO 8601 timestamp indicating when the task exited "Pending" (or ``null`` if it is still |
|             |         | Pending)                                                                                 |
+-------------+---------+------------------------------------------------------------------------------------------+

Note
----

+------------+----------+----------------------------------+
| Property   | Type     | Description                      |
+============+==========+==================================+
| id         | String   | ID of the note (globally unique) |
+------------+----------+----------------------------------+
| text       | String   | Text of note                     |
+------------+----------+----------------------------------+
| timestamp  | String   | Time of creation                 |
+------------+----------+----------------------------------+

Report
------

A Report has cutom properties added by each module. Which poperties exist on a report will depend on which modules provided analysis on the analyzed sample.

The following general properties should always exist on a report:

+------------------+------------------+--------------------------------------------------------------------------------------------+
| Property         | Type             | Description                                                                                |
+==================+==================+============================================================================================+
| Report Metadata  | Object           | Object with properties "Scan Time" and "Scan ID" which correspond to task ID and timestamp |
+------------------+------------------+--------------------------------------------------------------------------------------------+
| tags             | Array<String>    | List of tags associated with the task                                                      |
+------------------+------------------+--------------------------------------------------------------------------------------------+
