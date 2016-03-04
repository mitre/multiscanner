import os
import sys
import json
import responses
import unittest

CWD = os.path.dirname(os.path.abspath(__file__))
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow import of api.py
if os.path.join(MS_WD, 'utils') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'utils'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

import multiscanner
import api


HTTP_OK = 200
HTTP_CREATED = 201


class TestURLCase(unittest.TestCase):
    def setUp(self):
        self.app = api.app.test_client()

    def test_index(self):
        expected_response = {'Message': 'True'}
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, HTTP_OK)
        self.assertEqual(json.loads(resp.data), expected_response)
