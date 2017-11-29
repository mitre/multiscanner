Developing an Analytic
======================

Enabling analytics and advanced queries is the primary advantage of running several tools against a sample, extracting as much information as possible, and storing the output in a common datastore. For example, the following types of analytics and queries might be of interest:

- cluster samples
- outlier samples
- samples for deep-dive analysis
- gaps in current toolset
- machine learning analytics on tool outputs

Analytic development is currently ad hoc. Until interfaces are created to standardize development, the [Current Analytics](../use/use-analytics.md) page might prove useful - it contains development details of the **ssdeep** analytic.

Here's the [ssdeep code](https://github.com/mitre/multiscanner/blob/feature-celery/analytics/ssdeep_analytics.py) to use as a reference for how one might implement an analytic.