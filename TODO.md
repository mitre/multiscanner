This is a list of things that are wanted features

# Feature Updates #
- **Better output** - Printing json to the console is not super pretty. Maybe making an HTML output available for an analyst?
- **Module logging** - Create an API that allows modules to log errors and messages to a file.
- **Multiprocessing** - Currently modules are only run as threads, giving modules access to a multiprocessing pool for cpu intensive modules would be good.
- **Ability for modules to submit files** - Having modules be able to extract files that should be scanned and included in the report could be helpful in some use cases.
- **Maliciousness Weight** - Allow an analyst to define custom weights to results to priorities what to look at. Also having a "is malicious" flag if a file breaches a threshold
- **REST API** - Creating a script that provides a web api to submit files and pull reports.

# New Modules #
- OPSWAT Metascan
- PEframe https://github.com/guelfoweb/peframe
