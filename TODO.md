This is a list of things that are wanted features

# Minor Changes #
- **Config passing** - For the API, having multiscan() accept a dictionary/config object instead of a config file would be useful
- **Unzip and scan zips** - Allowing the analyst to provide a password protected zip to scan may be useful

# Feature Updates #
- **Storage Backends** - A plugin type architecture for storing results would be fantastic. Something for Elasticsearch and MongoDB.
- **REST API** - Creating a script that provides a web api to submit files and pull reports.
- **Better output** - Printing json to the console is not super pretty. Maybe making an HTML output available for an analyst?
- **Ability for modules to submit files** - Having modules be able to extract files that should be scanned and included in the report could be helpful in some use cases.
- **Maliciousness Weight** - Allow an analyst to define custom weights to results to priorities what to look at. Also having a "is malicious" flag if a file breaches a threshold

# New Modules #
- Cuckoo Sandbox
- OPSWAT Metascan