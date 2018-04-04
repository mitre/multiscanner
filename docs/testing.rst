Testing
=======

Running the MultiScanner test suite is fairly straight forward. We use the `pytest framework <https://docs.pytest.org/en/latest/>`_, which you can install by running::

    $ pip install pytest

After that, simply cd into the top level multiscanner directory and run the command::

    $ pytest

This will automatically find all the tests in the tests/ directory and run them. We encourage developers of new modules and users to contribute to our testing suite!

Front-end Tests with Selenium
-----------------------------

Running front-end tests with Selenium requires installation and configuration outside of the Python environment, namely
the installation of Firefox and geckodriver.

1. Install Firefox.
2. Download latest geckodriver release from `GitHub <https://github.com/mozilla/geckodriver/releases>`_.
3. Add geckodriver to system path.

Additional information about geckodriver setup can be found
`here <https://developer.mozilla.org/en-US/docs/Mozilla/QA/Marionette/WebDriver#Setting_up_the_geckodriver_executable>`_.

If pytest is unable to find Firefox or geckodriver, the front-end tests will be skipped. This is indicated by a
's' in the pytest output.

Tests have been run successfullly with Firefox 58 and geckodriver 0.19.1 on macOS and Ubuntu 14.04, 16.04.

CentOS
^^^^^^
The Firefox version available in the base repo is too far out-of-date to be compatible with the tests. Manually update
Firefox to the latest version.

1. Remove old version of Firefox::

      $ yum remove firefox

2. You may need to install these dependencies for Firefox::

      $ yum install -y gtk3 glib-devel glib pango pango-devel

3. Download latest version of Firefox::

      $ cd /usr/local
      $ curl -L http://ftp.mozilla.org/pub/firefox/releases/58.0/linux-x86_64/en-US/firefox-58.0.tar.bz2 | tar -xjf

4. Add symlink to bin dir::

      $ ln -s /usr/local/firefox/firefox /usr/bin/firefox
