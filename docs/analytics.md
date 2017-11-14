# Analytics #
Enabling analytics and advanced queries is the primary advantage of running 
several tools against a sample, extracting as much information as possible, and
storing the output in a common datastore.

The following are some example types of analytics and queries that may be of interest:

- cluster samples
- outlier samples
- samples for deep-dive analysis
- gaps in current toolset
- machine learning analytics on tool outputs
- others

## ssdeep Comparison ##
Fuzzy hashing is an effective method to identify similar files based on common
byte strings despite changes in the byte order and strcuture of the files.
[ssdeep](https://ssdeep-project.github.io/ssdeep/index.html) provides a fuzzy
hash implementation and provides the capability to compare hashes.

Comparing ssdeep hashes at scale is a challenge. [[1]](https://www.virusbulletin.com/virusbulletin/2015/11/optimizing-ssdeep-use-scale/)
originally described a method for comparing ssdeep hashes at scale.

The ssdeep analytic computes ```ssdeep.compare``` for all samples where the
result is non-zero and provides the capability to return all samples clustered
based on the ssdeep hash.

### Elasticsearch ###
When possible, it can be effective to push work to the Elasticsearch cluster
which support horizontal scaling. For the ssdeep comparison, Elasticsearch 
[NGram  Tokenizers](https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-ngram-tokenizer.html)
are used to compute 7-grams of the chunk and double-chunk portions
of the ssdeep hash as described here [[2]](http://www.intezer.com/intezer-community-tip-ssdeep-comparisons-with-elasticsearch/).
This prevents ever comparing two ssdeep hashes where the result will be zero.

### Python ###
Because we need to compute ```ssdeep.compare```, the ssdeep analytic cannot be
done entirely in Elasticsearch. Python is used to query Elasicsearch, compute
```ssdeep.compare``` on the results, and update the documents in Elasticsearch.

### Deployment ###
We use a Celery beat task to kick off the ssdeep comparison nightly at 2am local time, when the system is at lower user loads. This ensures that the analytic will be run on all samples without adding an exorbinant load to the system.
