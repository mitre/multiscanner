# ElasticSearch Usage Notes #
Starting with ElasticSearch 2.X, field names may no longer contain '.' (dot) characters. Thus, the `elasticsearch_storage` module adds a pipeline called 'dedot' with a processor to replace dots in field names with underscores.

## Setup ##
Add the following to your elasticsearch.yml config for the dedot processor to work:

```
script.painless.regex.enabled = true
```

If planning to use the Multiscanner web UI, also add the following:

```
http.cors.enabled: true
http.cors.allow-origin: "<yourOrigin>"
```