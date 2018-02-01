import os
import sys
import json
import requests

from flask import Flask
from flask_testing import LiveServerTestCase

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of app.py
if os.path.join(MS_WD, 'web') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'web'))
# Allow import of sql_driver
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

# get the flask web app
from app import app as flask_app

proxies = {
  "http": None,
  "https": None,
}

class MyTest(LiveServerTestCase):

    def create_app(self):
        app = flask_app
        app.config.update(
            TESTING=True,
            LIVESERVER_PORT=8943,
            LIVESERVER_TIMEOUT=10)
        return app

    def test_is_server_up(self):
        resp = requests.get(self.get_server_url(), proxies=proxies)
        self.assertEqual(resp.status_code, 200)
