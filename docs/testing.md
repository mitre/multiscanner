# Testing #
Running the MultiScanner test suite is fairly straight forward. We use the [pytest framework](https://docs.pytest.org/en/latest/), which you can install by running ```$ pip install pytest```.

After that, simply cd into the top level multiscanner directory and run the command: ```$ pytest```

This will automatically find all the tests in the tests/ directory and run them. We encourage developers of new modules and users to contribute to our testing suite!

## Front-end Tests with Selenium ##
Running front-end tests with Selenium requires installation and configuration outside of the Python environment, namely
the installation of Firefox and geckodriver.

1. Install Firefox.
1. Download latest geckodriver release from [GitHub](https://github.com/mozilla/geckodriver/releases).
1. Add geckodriver to system path.

Additional information about geckodriver setup can be found
[here](https://developer.mozilla.org/en-US/docs/Mozilla/QA/Marionette/WebDriver#Setting_up_the_geckodriver_executable).

If pytest is unable to find Firefox or geckodriver, the front-end tests will be skipped. This is indicated by a
's' in the pytest output.

Tests have been run successfullly on macOS and Ubuntu 14.04, 16.04. There are known issues with CentOS 7.
