import os
import json
import re
import socket
import shutil
import tempfile
from threading import Thread

from io import BytesIO
try:
    # py3k
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    # py2.7
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


def start_mock_server(file_content):
    port = get_free_port()

    class MockServerRequestHandler(BaseHTTPRequestHandler):
        '''adapted from https://realpython.com/testing-third-party-apis-with-mock-servers
        serves file in file_content
        returns in chunks if chunked=true is part of url
        requires any Basic auth if auth=true is part of url
        :returns: base URL
        '''
        CHUNK_SIZE = 1024

        def do_GET(self):
            if 'auth=true' in self.path:
                if not 'Authorization' in self.headers:
                    self.send_response(401)
                    self.send_header('Www-Authenticate', 'Basic realm="foo"')
                    self.end_headers()
                    return
            if re.search(re.compile(r'/downloads/.*'), self.path):
                # Add response status code.
                self.send_response(200)

                # Add response headers.
                self.send_header('Content-Type', 'application/application/x-gzip;')

                # Add response content.
                if 'chunked=true' in self.path:
                    self.send_header('Transfer-Encoding', 'chunked')
                    self.send_header('Connection', 'close')
                    self.end_headers()

                    stream = BytesIO(file_content)
                    while True:
                        data = stream.read(self.CHUNK_SIZE)
                        # python3.[0-4] cannot easily format bytes (see PEP 461)
                        self.wfile.write(("%X\r\n" % len(data)).encode('ascii'))
                        self.wfile.write(data)
                        self.wfile.write(b"\r\n")
                        # If there's no more data to read, stop streaming
                        if not data:
                            break

                else:
                    self.end_headers()
                    self.wfile.write(file_content) # nonchunked

                # Ensure any buffered output has been transmitted and close the stream
                self.wfile.flush()
                return
            if result_status is None:
                self.send_response(404)
                self.end_headers()
                return

    mock_server = HTTPServer(('localhost', port), MockServerRequestHandler)
    mock_server_thread = Thread(target=mock_server.serve_forever)
    mock_server_thread.setDaemon(True)
    mock_server_thread.start()
    return 'http://localhost:{port}'.format(port=port)
