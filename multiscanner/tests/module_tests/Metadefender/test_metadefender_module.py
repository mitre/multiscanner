'''
Created on Sep 16, 2016

Unit test for the Metadefender module
'''
import unittest
import os
import mock
import json

CWD = os.path.dirname(os.path.abspath(__file__))

from multiscanner.modules.Antivirus import Metadefender

RANDOM_INPUT_FILES = ['input1', 'input2', 'input3']

SCAN_IDS = ['hyayv9g1x4hmxahvkmyimh3j3tj3ivvk',
            'nlktbcadvlk7a40yid3yf3jmbad19eq5',
            'a956bwcc8wdvctmdjsnp54qubdytt6oe']
MSG_SERVER_UNAVAILABLE = 'Server unavailable, try again later'
FILE_200_COMPLETE_REPORT = 'retrieval_responses/200_found_complete.json'
FILE_200_INCOMPLETE_REPORT = 'retrieval_responses/200_found_incomplete.json'


class MockResponse(object):
    '''
    This class mocks a requests.Response object
    '''

    def __init__(self, status_code, response_string):
        self.status_code = status_code
        self.response_string = response_string

    def json(self):
        # It's important that we use a string and attempt to
        # jsonify it, because that is what the requests library
        # is doing, and why it throws a ValueError if the response
        # isn't valid JSON
        return json.loads(self.response_string)


def generate_scan_id(filename):
    return filename + '_scan_ID'

# ---------------------------------------------------------------------
#  Mock Requests methods for sample submission
# ---------------------------------------------------------------------


def mocked_requests_post_sample_submitted(*args, **kwargs):
    '''
    Mocks the requests.post method. Returns what Metadefender
    would return on a successful sample submission
    '''
    filename = kwargs['headers']['filename']
    json_resp = json.dumps({'data_id': generate_scan_id(filename)})
    response = MockResponse(200, json_resp)
    return response


def mocked_requests_post_sample_failed_w_msg(*args, **kwargs):
    '''
    Mocks the requests.post method. Returns what Metadefender
    would return on a submission that failed due to the
    server being unavailable
    '''
    json_resp = json.dumps({'err': MSG_SERVER_UNAVAILABLE})
    response = MockResponse(500, json_resp)
    return response


def mocked_requests_post_sample_failed_no_msg(*args, **kwargs):
    '''
    Mocks the requests.post method. Simulates Metadfender
    returning a 500 error with no error message
    '''
    json_resp = 'None'
    response = MockResponse(500, json_resp)
    return response

# ---------------------------------------------------------------------
#  Mock Requests methods for scan retrieval
# ---------------------------------------------------------------------


def mocked_requests_get_sample_200_success(*args, **kwargs):
    '''
    Mocks the requests.get method. Returns what Metadefender
    would return on a successful request for scan retrieval
    '''
    file_200_resp = os.path.join(CWD, FILE_200_COMPLETE_REPORT)
    with open(file_200_resp, 'r') as jsonfile:
        json_resp = jsonfile.read().replace('\n', '')
    response = MockResponse(200, json_resp)
    return response


def mocked_requests_get_sample_200_not_found(*args, **kwargs):
    '''
    Mocks the requests.get method. Returns what Metadefender
    would return on a request for which no data is found.
    Metadefender returns a 200 even though a 404 seems more appropriate...
    '''
    json_resp = json.dumps({SCAN_IDS[0]: 'Not Found'})
    response = MockResponse(200, json_resp)
    return response


def mocked_requests_get_sample_200_in_progress(*args, **kwargs):
    '''
    Mocks the requests.get method. Returns what Metadefender
    would return on a successful request for scan retrieval
    when scan is not finished
    '''
    file_200_resp = os.path.join(CWD, FILE_200_INCOMPLETE_REPORT)
    with open(file_200_resp, 'r') as jsonfile:
        json_resp = jsonfile.read().replace('\n', '')
    response = MockResponse(200, json_resp)
    return response

# Unit test class


class MetadefenderTest(unittest.TestCase):

    def setUp(self):
        # Create random binary file
        for fname in RANDOM_INPUT_FILES:
            with open(fname, 'wb') as fout:
                fout.write(os.urandom(1024))

    def tearDown(self):
        # Delete all the files we created
        for fname in RANDOM_INPUT_FILES:
            os.remove(fname)

    def create_conf_short_timeout(self):
        conf = Metadefender.DEFAULTCONF
        conf['timeout'] = 4
        conf['running timeout'] = 2
        conf['fetch delay seconds'] = 1
        conf['poll interval seconds'] = 1
        return conf
    # ---------------------------------------------------------------------
    # This section tests the logic that interprets Metadefender's
    # possible responses to sample submission requests
    # ---------------------------------------------------------------------

    @mock.patch('Metadefender.requests.post', side_effect=mocked_requests_post_sample_submitted)
    def test_submit_sample_success(self, mock_get):
        '''
        Tests Metadefender._submit_sample()'s handling of a successful response from
        the server
        '''
        print('Running test_submit_sample_success')
        submit_resp = Metadefender._submit_sample(RANDOM_INPUT_FILES[0], 'scan_url', 'user_agent')
        self.assertEquals(submit_resp['status_code'], 200)
        self.assertEquals(submit_resp['error'], None)
        self.assertEquals(submit_resp['scan_id'], generate_scan_id(RANDOM_INPUT_FILES[0]))

    @mock.patch('Metadefender.requests.post', side_effect=mocked_requests_post_sample_failed_w_msg)
    def test_submit_sample_fail_unavailable(self, mock_get):
        '''
        Tests Metadefender._submit_sample()'s handling of a submission that fails due to
        a 500 error
        '''
        print('Running test_submit_sample_fail_unavailable')
        submit_resp = Metadefender._submit_sample(RANDOM_INPUT_FILES[1], 'scan_url', 'user_agent')
        self.assertEquals(submit_resp['status_code'], 500)
        self.assertEquals(submit_resp['error'], MSG_SERVER_UNAVAILABLE)
        self.assertEquals(submit_resp['scan_id'], None)

    @mock.patch('Metadefender.requests.post', side_effect=mocked_requests_post_sample_failed_no_msg)
    def test_submit_sample_fail_unavailable_no_msg(self, mock_get):
        '''
        Tests Metadefender._submit_sample()'s handling of a submission that fails due to
        a 500 error and where no message is returned
        '''
        print('Running test_submit_sample_fail_unavailable_no_msg')
        submit_resp = Metadefender._submit_sample(RANDOM_INPUT_FILES[1], 'scan_url', 'user_agent')
        self.assertEquals(submit_resp['status_code'], 500)
        self.assertEquals(submit_resp['error'], Metadefender.MD_HTTP_ERR_CODES[500])
        self.assertEquals(submit_resp['scan_id'], None)

    # ---------------------------------------------------------------------
    # This section tests the logic for parsing Metadefender's responses
    # to requests for analysis results
    # ---------------------------------------------------------------------
    @mock.patch('Metadefender.requests.get', side_effect=mocked_requests_get_sample_200_success)
    def test_get_results_200_success(self, mock_get):
        '''
        Tests Metadefender._parse_scan_result()'s handling of a complete
        analysis report
        '''
        print('Running test_get_results_200_success')
        report_resp = Metadefender._retrieve_scan_results('results_url', SCAN_IDS[0])
        is_scan_complete, parsed_resp = Metadefender._parse_scan_result(report_resp)
        self.assertEquals(is_scan_complete, True)
        self.assertEquals(parsed_resp['overall_status'], Metadefender.STATUS_SUCCESS)

        engine_results = parsed_resp['engine_results']
        for engine_result in engine_results:
            engine_name = engine_result['engine_name']
            scan_result = engine_result['scan_result']
            threat_found = engine_result['threat_found']
            if engine_name == 'ClamAV':
                self.assertEquals(scan_result, 'Infected/Known')
                self.assertEquals(threat_found, 'Heuristics.PDF.ObfuscatedNameObject')
            elif engine_name == 'Ahnlab':
                self.assertEquals(scan_result, 'Infected/Known')
                self.assertEquals(threat_found, 'Trojan/Win32.Inject.C1515213')
            elif engine_name == 'ESET':
                self.assertEquals(scan_result, 'No threats Found')
                self.assertEquals(threat_found, '')
            elif engine_name == 'Avira':
                self.assertEquals(scan_result, 'No threats Found')
                self.assertEquals(threat_found, '')
            else:
                self.fail('Unexpected Engine: %s' % engine_name)

    @mock.patch('Metadefender.requests.get', side_effect=mocked_requests_get_sample_200_not_found)
    def test_get_results_200_not_found(self, mock_get):
        '''
        Tests Metadefender._parse_scan_result()'s handling of a 200 response
        where the scan ID was not found. The module is supposed to interpret
        this to mean that the analysis is 'pending'
        '''
        print('Running test_get_results_200_not_found')
        report_resp = Metadefender._retrieve_scan_results('results_url', SCAN_IDS[0])
        is_scan_complete, parsed_resp = Metadefender._parse_scan_result(report_resp)
        self.assertEquals(is_scan_complete, False)
        self.assertEquals(parsed_resp['overall_status'], Metadefender.STATUS_PENDING)

        engine_results = parsed_resp['engine_results']
        if len(engine_results) != 0:
            self.fail('Engine result list should be empty')

    @mock.patch('Metadefender.requests.get', side_effect=mocked_requests_get_sample_200_in_progress)
    def test_get_results_200_succes_in_progress(self, mock_get):
        '''
        Tests Metadefender._parse_scan_result()'s handling of a 200 response
        where the scan ID was found but the scan is not complete
        '''
        print('Running test_get_results_200_succes_in_progress')
        report_resp = Metadefender._retrieve_scan_results('results_url', SCAN_IDS[0])
        is_scan_complete, parsed_resp = Metadefender._parse_scan_result(report_resp)
        self.assertEquals(is_scan_complete, False)
        self.assertEquals(parsed_resp['overall_status'], Metadefender.STATUS_PENDING)
        msg = parsed_resp['msg']
        if 'percent complete: 10' not in msg:
            self.fail('Progress percentage not present')
        engine_results = parsed_resp['engine_results']
        if len(engine_results) != 0:
            self.fail('Engine result list should be empty')

    # ---------------------------------------------------------------------
    # This section tests the entire scan() method
    # ---------------------------------------------------------------------
    @mock.patch('Metadefender.requests.get', side_effect=mocked_requests_get_sample_200_success)
    @mock.patch('Metadefender.requests.post', side_effect=mocked_requests_post_sample_submitted)
    def test_scan_complete_success(self, mock_post, mock_get):
        '''
        Test for a perfect scan. No submission errors, no retrieval errors
        '''
        print('Running test_scan_complete_success')
        resultlist, metadata = Metadefender.scan(RANDOM_INPUT_FILES,
                                                 conf=self.create_conf_short_timeout())
        self.assertEquals(len(resultlist), len(RANDOM_INPUT_FILES))
        for scan_res in resultlist:
            self.assertEquals(scan_res[1]['overall_status'], Metadefender.STATUS_SUCCESS)

    @mock.patch('Metadefender.requests.get', side_effect=mocked_requests_get_sample_200_in_progress)
    @mock.patch('Metadefender.requests.post', side_effect=mocked_requests_post_sample_submitted)
    def test_scan_timeout_scan_in_progress(self, mock_post, mock_get):
        '''
        Test for a scan where analysis time exceeds timeout period
        '''
        print('Running test_scan_timeout_scan_in_progress')
        resultlist, metadata = Metadefender.scan(RANDOM_INPUT_FILES,
                                                 conf=self.create_conf_short_timeout())
        self.assertEquals(len(resultlist), len(RANDOM_INPUT_FILES))
        for scan_res in resultlist:
            self.assertEquals(scan_res[1]['overall_status'], Metadefender.STATUS_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
