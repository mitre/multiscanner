RESTful API
===========

The MultiScanner RESTful API is provided by a Flask app that supports accessing submitted samples, and information about tasks, reports, and modules.

The API endpoints all have Cross Origin Resource Sharing (CORS) enabled. By default it will allow requests from any port on localhost. Change this setting by modifying the ``cors`` setting in the ``api`` section of the api config file.

TODO: add endpoint-does-not-exist error; currently uses inappropriate "task ID not found"

Download Samples
----------------

Download samples that have been submitted to MultiScanner for analysis.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v1/files/<sha256>?raw={t|f}                    | File download                            |
+--------+-----------------------------------------------------+------------------------------------------+
| Download sample with the specified SHA256 hash. Download defaults to password protected zip; use `raw=t`|
| to download a raw binary instead.                                                                       |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v1/tasks/<task_id>/file?raw={t|f}              | File download                            |
+--------+-----------------------------------------------------+------------------------------------------+
| Download sample associated with the given `task_id`. Download defaults to password protected zip; use   |
| `raw=t` to download a raw binary instead.                                                               |
+--------+------------------------------------------------------------------------------------------------+

Tasks
-----

View, submit, and search analysis tasks and their resulting reports.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v1/tasks                                       | List of tasks                            |
+--------+-----------------------------------------------------+------------------------------------------+
| Get a list of tasks in MultiScanner                                                                     |
|                                                                                                         |
| DONE: remove Tasks wrapper                                                                              |
+--------+-----------------------------------------------------+------------------------------------------+
| POST   | /api/v1/tasks                                       | JSON object with ``task_ids`` key,       |
|        |                                                     | holding list of IDs                      |
+--------+-----------------------------------------------------+------------------------------------------+
| Submit file sample via POST file, and receive a task ID for the analysis of the submission.             |
|                                                                                                         |
| Sample POST usage: `curl -i -X POST http://localhost:8080/api/v1/tasks -F file=@/bin/ls`                |
|                                                                                                         |
| Sample response: ``{ "task_ids": [5, 6, 7] }``                                                          |
|                                                                                                         |
| Expects a file in the request body named ``file``, and also admits the following HTTP form keys:        |
|  * ``duplicate`` - either ``rescan`` (do a scan even if this file has been previously submitted)        |
|      or ``latest`` (use the latest scan that has already been done on this file, if one exists)         |
|  * ``modules`` - TODO                                                                                   |
|  * ``archive-analyze`` - set to ``true`` to unpack submission as an archive before analysis             |
|  * ``archive-password`` - password to use when unpacking archive submission, UTF-8 encoded              |
|  * ``upload_type`` - use and set to ``import`` to submit a JSON representation of a MultiScanner task   |
|       downloaded from  ``/api/v1/tasks/<task_id>/report`` instead of a sample file for analysis         |
|  * Any other keys supplied are saved as keys on the task's metadata                                     |
|                                                                                                         |
| DONE: remove Message wrapper                                                                            |
|                                                                                                         |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v1/tasks/<task_id>                             | Task                                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Get information about the task with the given `task_id`                                                 |
|                                                                                                         |
| DONE: remove Tasks wrapper                                                                              |
+--------+-----------------------------------------------------+------------------------------------------+
| DELETE | /api/v1/tasks/<task_id>                             | Confirmation text                        |
+--------+-----------------------------------------------------+------------------------------------------+
| Delete task with the given `task_id`                                                                    |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v1/tasks/search                                | List with a single task                  |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of most recent report for matching samples. For use with Lucene queries                    |
|                                                                                                         |
| * Supplies its parameters directly to ElasticSearch                                                     |
| * TODO: example search params                                                                           |
| * TODO: extremely brittle; passes on ES errors as 200 responses                                         |
| * TODO: clean up output to send only task results instead of metadata                                   |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v1/tasks/search/history                        | List of tasks                            |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of all reports for matching samples                                                        |
|                                                                                                         |
| Supplies its parameters directly to ElasticSearch (TODO: same as above)                                 |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v1/tasks/<task_id>/maec                        | MAEC file                                |
+--------+-----------------------------------------------------+------------------------------------------+
| Download the Cuckoo MAEC 5.0 report, if it exists                                                       |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v1/tasks/<task_id>/pdf                         | Human-readable PDF document              |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive PDF report for task                                                                             |
+--------+-----------------------------------------------------+------------------------------------------+
| GET    | /api/v1/tasks/<task_id>/report?d={t|f}              | Analysis report in JSON                  |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive report in JSON; set ``d=t`` to download or ``d=f`` to view                                      |
|                                                                                                         |
| DONE*: remove "Report" wrapper EV: For download response, but unsure if we need internally              |
+--------+-----------------------------------------------------+------------------------------------------+ 

Tags
----

These endpoints manipulate tags on a report. To view tags on a report, use the ``tasks/<task_id>/report`` endpoint.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v1/tags                                        | List of ``{ key, doc_count }`` objects   |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of all tags in use. Response is a list of objects each with a ``key`` property (the tag)   |
| and ``doc_count`` property (the number of documents in which the tag appears).                          |
|                                                                                                         |
| * TODO: remove Tags wrapper                                                                             |
+--------+-----------------------------------------------------+------------------------------------------+
| POST   | /api/v1/tasks/<task_id>/tags                        | Confirmation message                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Add a tag to a task. Use HTTP from param ``tag``, i.e., ``tag=...`` with                                |
| ``Content-type: application/x-www-form-urlencoded`` header                                              |
|                                                                                                         |
| TODO: sensitive to Content-type -- okay? (same with DELETE delow)                                       |
+--------+-----------------------------------------------------+------------------------------------------+
| DELETE | /api/v1/tasks/<task_id>/tags                        | Confirmation message                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Remove a tag from a task. Use HTTP from param ``tag``, i.e., ``tag=...`` with                           |
| ``Content-type: application/x-www-form-urlencoded`` header                                              |
+--------+-----------------------------------------------------+------------------------------------------+


Notes
-----

TODO: Notes are associated with a sample, but here are modified and accessed via ``task_id``. If you ask for notes on two different tasks on the same sample, you get the same notes.

TODO: responses might be needlessly large, with lots of Elastic info -- we really just want the note, not shard info, etc.

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v1/tasks/<task_id>/notes                       | List of notes                            |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of this tasks notes                                                                        |
|                                                                                                         |
| TODO: Optionally takes ``ts`` and ``uid`` query-string arguments: ``/notes?ts=...&uid=...``             |
+--------+-----------------------------------------------------+------------------------------------------+
| POST   | /api/v1/tasks/<task_id>/notes                       | Extensive ES object w/ note's ``_id``    |
+--------+-----------------------------------------------------+------------------------------------------+
| Add a note to task, using the HTTP parameter ``text=...``                                               |
|                                                                                                         |
| * DONE*: should POST body this just be the text itself..? we don't use other fields EV: Just success msg|
| * DONE*: should response just be the note ID? and optionally text, and maybe sample ID                  |
+--------+-----------------------------------------------------+------------------------------------------+
| PUT    | /api/v1/tasks/<task_id>/notes/<note_id>             | Extensive ES object w/ note's ``_id``    |
+--------+-----------------------------------------------------+------------------------------------------+
| Edit a notesing the HTTP parameter ``text=...`` (TODO: same as above)                                   |
+--------+-----------------------------------------------------+------------------------------------------+
| DELETE | /api/v1/tasks/<task_id>/notes/<note_id>             | Extensive ES object w/ note's ``_id``    |
+--------+-----------------------------------------------------+------------------------------------------+
| Delete a note (DONE*: response note above)                                                              |
+--------+-----------------------------------------------------+------------------------------------------+


Modules/Other
-------------

+--------+-----------------------------------------------------+------------------------------------------+
| Method | URI                                                 | Response type                            |
+========+=====================================================+==========================================+
| GET    | /api/v1/modules                                     | JSON object with module names as keys    |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive an object whose keys are the names of available of modules. The corresponding value of each key |
| is a boolean that indicates whether the module is currently activated or not.                           |
|                                                                                                         |
| * DONE: JSON has a native boolean -- use ``true``/``false`` instead of strings                          |
| * DONE: remove Modules wrapper?                                                                         |
+--------------------------------------------------------------+------------------------------------------+
|| GET    | /api/v1/analytics/ssdeep_compare                    | TODO                                    |
+--------+-----------------------------------------------------+------------------------------------------+
| Run ssdeep.compare analytic                                                                             |
+--------------------------------------------------------------+------------------------------------------+
| GET    | /api/v1/analytics/ssdeep_group                      | TODO                                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Receive list of sample hashes grouped by ssdeep hash                                                    |
+--------------------------------------------------------------+------------------------------------------+
| GET    | /                                                   | Test response object                     |
+--------+-----------------------------------------------------+------------------------------------------+
| Test functionality. Should produce: ``{'Message': 'True'}``  (DONE*: use boolean)                       |
+---------------------------------------------------------------------------------------------------------+            

