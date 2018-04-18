RESTful API
===========

The RESTful API is provided by a Flask app that supports the following operations:

====== ======================================= =======================================
Method URI                                     Description
====== ======================================= =======================================
GET    /                                       Test functionality. Should produce: ``{'Message': 'True'}``
GET    /api/v1/files/<sha256>?raw={t|f}        Download sample, defaults to passwd protected zip
GET    /api/v1/modules                         Receive list of modules available
GET    /api/v1/tags                            Receive list of all tags in use
GET    /api/v1/tasks                           Receive list of tasks in MultiScanner
POST   /api/v1/tasks                           POST file and receive report id.
                                               Sample POST usage:
                                               ``curl -i -X POST http://localhost:8080/api/v1/tasks -F file=@/bin/ls``
GET    /api/v1/tasks/<task_id>                 Receive task in JSON format
DELETE /api/v1/tasks/<task_id>                 Delete task_id
GET    /api/v1/tasks/search/                   Receive list of most recent report for matching samples
GET    /api/v1/tasks/search/history            Receive list of most all reports for matching samples
GET    /api/v1/tasks/<task_id>/file?raw={t|f}  Download sample, defaults to passwd protected zip
GET    /api/v1/tasks/<task_id>/maec            Download the Cuckoo MAEC 5.0 report, if it exists
GET    /api/v1/tasks/<task_id>/notes           Receive list of this tasks notes
POST   /api/v1/tasks/<task_id>/notes           Add a note to task
PUT    /api/v1/tasks/<task_id>/notes/<note_id> Edit a note
DELETE /api/v1/tasks/<task_id>/notes/<note_id> Delete a note
GET    /api/v1/tasks/<task_id>/report?d={t|f}  Receive report in JSON, set d=t to download
GET    /api/v1/tasks/<task_id>/pdf             Receive PDF report
POST   /api/v1/tasks/<task_id>/tags            Add tags to task
DELETE /api/v1/tasks/<task_id>/tags            Remove tags from task
GET    /api/v1/analytics/ssdeep_compare        Run ssdeep.compare analytic
GET    /api/v1/analytics/ssdeep_group          Receive list of sample hashes grouped by ssdeep hash
====== ======================================= =======================================

The API endpoints all have Cross Origin Resource Sharing (CORS) enabled. By default it will allow requests from any port on localhost. Change this setting by modifying the ``cors`` setting in the ``api`` section of the api config file.
