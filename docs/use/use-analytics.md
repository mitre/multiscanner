Analytics
=========

Currently, one analytic is available.

**[ssdeep]**

Fuzzy hashing is an effective method to identify similar files based on common byte strings despite changes in the byte order and structure of the files. [ssdeep](https://ssdeep-project.github.io/ssdeep/index.html) provides a fuzzy hash implementation and provides the capability to compare hashes. The [Virus Bulletin](https://www.virusbulletin.com/virusbulletin/2015/11/optimizing-ssdeep-use-scale/) originally described a method for comparing ssdeep hashes at scale. 

Comparing ssdeep hashes at scale is a challenge. Therefore, the ssdeep analytic computes ```ssdeep.compare``` for all samples where the result is non-zero and provides the capability to return all samples clustered based on the ssdeep hash. Furthermore,

- When possible, it can be effective to push work to the Elasticsearch cluster which support horizontal scaling. For the ssdeep comparison, Elasticsearch [NGram  Tokenizers](https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-ngram-tokenizer.html)
are used to compute 7-grams of the chunk and double-chunk portions of the ssdeep hash as described here [[2]](http://www.intezer.com/intezer-community-tip-ssdeep-comparisons-with-elasticsearch/). This prevents the comparison of two ssdeep hashes where the result will be zero.

- Because we need to compute ```ssdeep.compare```, the ssdeep analytic cannot be done entirely in Elasticsearch. Python is used to query Elasicsearch, compute ```ssdeep.compare``` on the results, and update the documents in Elasticsearch.

- [celery beat](http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html) is used to schedule and kick off the ssdeep comparison task nightly at 2am local time, when the system is experiencing less load from users. This ensures the analytic will be run on all samples without adding an exorbinant load to the system.