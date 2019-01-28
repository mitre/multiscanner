from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import socket
from threading import Thread

import requests

# https://realpython.com/blog/python/testing-third-party-apis-with-mock-servers/


class MockHTTPServerRequestHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        # add response codes
        self.send_response(requests.codes.okay)

        # add response headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'dataType, accept, authoriziation')
        self.end_headers()

    def do_GET(self):
        # add response codes
        self.send_response(requests.codes.ok)

        # add response headers
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

        # add response content
        response_content = json.dumps({'Message': 'Success'})
        self.wfile.write(response_content.encode('utf-8'))
        return

    def do_POST(self):
        # add response codes
        self.send_response(requests.codes.created)

        # add response headers
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access=Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE, PUT')
        self.end_headers()

        # add response content
        response_content = json.dumps({'Message': {'task_ids': [1234]}})
        self.wfile.write(response_content.encode('utf-8'))
        return


def get_free_server_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


def start_mock_server(port=8080):
    mock_server = HTTPServer(('localhost', port), MockHTTPServerRequestHandler)
    mock_server_thread = Thread(target=mock_server.serve_forever)
    mock_server_thread.setDaemon(True)
    mock_server_thread.start()
