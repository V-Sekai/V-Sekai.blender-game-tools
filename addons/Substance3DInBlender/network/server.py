"""
Copyright (C) 2022 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# file: network/server.py
# brief: Web server
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import json
import traceback
import threading
import requests
import http.server
import http.client

from ..utils import SUBSTANCE_Utils
from .rest import SRE_Rest

from ..common import (
    Code_Response,
    Code_RequestType,
    SERVER_HOST,
    SERVER_ALLOW_LIST
)


class SRE_HTTPServer(http.server.HTTPServer):

    def run(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server_close()


class SRE_Handler(http.server.BaseHTTPRequestHandler):

    def _call_listeners(self, type, data):
        if data is not None:
            from ..api import SUBSTANCE_Api
            SUBSTANCE_Api.listeners_call(type, data)

    def _set_response(self, value):
        try:
            self.send_response(value)
            self.send_header("Content-type", "text/html")
            self.end_headers()
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Http response fail:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

    def handle(self):
        try:
            http.server.BaseHTTPRequestHandler.handle(self)
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Http handle fail:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

    def validateRequest(self, headers):
        _host = headers.get('Host').split(':')[0]
        return _host in SERVER_ALLOW_LIST

    def do_HEAD(self, s):
        if self.validateRequest(self.headers):
            self._set_response(200)

    def do_GET(self):
        if self.validateRequest(self.headers):
            self._call_listeners("get", self.path)
            self._set_response(200)
            self.wfile.write(bytes("<html><head><title>Title goes here.</title></head>", "utf-8"))
            self.wfile.write(bytes("<body><p>This is a test.</p></body></html>", "utf-8"))

    def do_POST(self):
        if self.validateRequest(self.headers):
            _content_len = int(self.headers.get('Content-Length'))
            _data = self.rfile.read(_content_len)

            if _data is not None:
                _json_data = json.loads(_data)
                self._call_listeners("post", _json_data)

            self._set_response(200)

    def do_PATCH(self):
        if self.validateRequest(self.headers):
            self._set_response(200)

    def log_message(self, format, *args):
        # Override this function to prevent log spam
        pass


class SRE_Server():
    def __init__(self):
        self.server = None
        self.thread = None
        self.host = SERVER_HOST
        self.port = None
        self.session = None
        self.rest = SRE_Rest()

    def is_running(self):
        if self.server:
            return True
        else:
            return False

    def get_port(self):
        return self.port

    def start(self):
        if self.server is None:
            self.server = SRE_HTTPServer((self.host, 0), SRE_Handler)
            self.port = self.server.server_port
            self.thread = threading.Thread(None, self.server.run)
            self.thread.daemon = True
            self.thread.start()

            return Code_Response.success
        return Code_Response.server_start_error

    def stop(self):
        if self.server is not None:
            if self.session is not None:
                self.session.close()
            self.server.shutdown()
            self.thread.join()
            self.server = None
            self.thread = None
            self.port = None
            self.session = None
            return Code_Response.success
        return Code_Response.server_stop_error

    def send_message(self, type, verb, endpoint, data={}, ignore_connection_error=False):
        if self.session is None:
            self.session = requests.Session()

        if type == Code_RequestType.r_sync:
            _result = self.rest.sync_request(
                self.session,
                verb,
                endpoint,
                data=data,
                ignore_connection_error=ignore_connection_error)
            return _result
        elif type == Code_RequestType.r_async:
            self.rest.async_request(
                self.session,
                verb,
                endpoint,
                data=data,
                ignore_connection_error=ignore_connection_error)
            return (Code_Response.success, None)
        else:
            return (Code_Response.api_server_send_type_error, None)
