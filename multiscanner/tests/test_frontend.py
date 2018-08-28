import os
import requests
import time

import pytest

from flask import url_for
from flask_testing import LiveServerTestCase
from .mocks import get_free_server_port, start_mock_server
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# get the flask web app
from multiscanner.web.app import app as flask_app

proxies = {
    "http": None,
    "https": None,
}

try:
    opts = Options()
    opts.add_argument('-headless')
    driver = webdriver.Firefox(firefox_options=opts)
except Exception as e:
    pytestmark = pytest.mark.skip

test_submitter_name = 'John Doe'
test_submitter_email = 'jdoe@local.domain'
test_submitter_org = 'Testers'
test_submitter_phone = '123-456-7890'
test_submission_desc = 'A test document submission'


class TestBase(LiveServerTestCase):

    @classmethod
    def setup_class(cls):
        cls.mock_server_port = get_free_server_port()
        start_mock_server(cls.mock_server_port)

    def create_app(self):
        app = flask_app
        app.config.update(
            TESTING=True,
            API_LOC='http://localhost:{}'.format(self.mock_server_port),
            LIVESERVER_PORT=8943,
            LIVESERVER_TIMEOUT=10)
        return app

    def setUp(self):
        """Set up test driver"""
        opts = Options()
        opts.add_argument('-headless')
        self.driver = webdriver.Firefox(firefox_options=opts)
        self.driver.get(self.get_server_url())

    def tearDown(self):
        self.driver.quit()

    def test_is_server_up(self):
        resp = requests.get(self.get_server_url(), proxies=proxies)
        self.assertEqual(resp.status_code, 200)


class TestSubmission(TestBase):

    def _add_files(self, files):
        for fname in files:
            data_file = Path(__file__).parent / 'test_files/{}'.format(fname)
            assert data_file.exists()

            # send file path
            self.driver.find_element_by_css_selector("input[type=\"file\"]").clear()
            self.driver.find_element_by_css_selector("input[type=\"file\"]").send_keys(str(data_file))

            # find file upload button
            # Note: Firefox doesn't like this...not actually the btn's id
            # self.driver.find_element_by_id('filesUpload').click()

    def _successful_submission(self):
        val = self.driver.find_element(By.CLASS_NAME, 'progress-bar')
        print('Progress bar: ' + str(val.text))
        return 'Submitted' in val.text

    def test_single_file_submission(self):
        """Test that a user is able to submit a single file.
        """
        self._add_files(['1.txt'])

        # Click seems to happen too quickly with a single file
        # Is there a way to wait for?
        time.sleep(1)

        # submit file
        self.driver.find_element_by_id('btn-scan').click()

        assert self._successful_submission()

    def test_multiple_file_submission(self):
        """Test that a user is able to submit multiple files.
        """
        self._add_files(['1.txt', '2.txt', '3.txt'])

        # Not clear all files are getting uploaded
        # Add similar wait from single file submission
        time.sleep(1)

        # submit files
        self.driver.find_element_by_id('btn-scan').click()

        assert self._successful_submission()

    def test_submission_with_metadata_fields(self):
        """Test that a user is able to submit file with metadata fields.
        """
        self._add_files(['1.txt'])

        self.driver.find_element_by_id('btn-opts').click()
        time.sleep(1)
        self.driver.find_element_by_id(
            'metadata-Submitter-Name').send_keys(test_submitter_name)
        self.driver.find_element_by_id(
            'metadata-Submission-Description').send_keys(test_submission_desc)
        self.driver.find_element_by_id(
            'metadata-Submitter-Email').send_keys(test_submitter_email)
        self.driver.find_element_by_id(
            'metadata-Submitter-Organization').send_keys(test_submitter_org)
        self.driver.find_element_by_id(
            'metadata-Submitter-Phone').send_keys(test_submitter_phone)

        # submit files
        self.driver.find_element_by_id('btn-scan').click()

        assert self._successful_submission()

    def test_help_button(self):
        """Test that the help button opens diaglog box.
        """

        # find help display and make sure it's hidden
        element = self.driver.find_element_by_id('help-modal')
        assert not(element.is_displayed())

        # click the help icon
        self.driver.find_element(
            By.XPATH,
            '/html/body/nav/div/div[2]/ul[2]/li[2]').click()

        # give it a second to open and then verify it's open
        time.sleep(1)
        element = self.driver.find_element_by_id('help-modal')
        self.assertEqual(element.get_property('hidden'), False)
        assert element.is_displayed()

    def test_change_tabs(self):
        """Test that the navigation tabs work.
        """
        self.driver.find_element(
            By.XPATH,
            '/html/body/nav/div/div[2]/ul[1]/li[2]/a').click()
        time.sleep(1)
        assert url_for('tasks') in self.driver.current_url

    # def test_search_functionality(self):
    #     """Test something about the search functionality.
    #     """
