"""
Copyright (C) 2021 Adobe.
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

# Substance in Blender Server
# 7/22/2020
import threading
import http.server


class SREHTTPServer(http.server.HTTPServer):
    """ Simple SRE Server """
    def run(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server_close()


class SREHandler(http.server.BaseHTTPRequestHandler):
    """ Simple SRE Handler """
    allowList = ['127.0.0.1', 'localhost']

    def log_message(self, format, *args):
        """ Override this function to prevent log spam """
        pass

    def _set_response(self, value):
        """ Respond to the request """
        try:
            self.send_response(value)
            self.send_header("Content-type", "text/html")
            self.end_headers()
        except Exception as e:
            print('Http response fail: ' + str(e))

    def validateRequest(self, headers):
        """ Validate the incoming request """
        host = headers.get('Host').split(':')[0]
        return host in SREHandler.allowList

    def do_HEAD(self, s):
        if self.validateRequest(self.headers):
            self._set_response(200)

    def do_GET(self):
        if self.validateRequest(self.headers):
            self._set_response(200)

    def do_POST(self):
        if self.validateRequest(self.headers):
            self._set_response(200)

    def do_PATCH(self):
        if self.validateRequest(self.headers):
            self._set_response(200)


class SREServer():
    """ SRE Server """
    def __init__(self):
        self.sre_server = None
        self.server_thread = None
        self.uri = None

    def run(self, host_name, port, handler=SREHandler):
        """ Set the name, port, handler and start the server thread """
        self.uri = host_name + ':' + str(port)
        self.sre_server = SREHTTPServer((host_name, port), handler)
        self.server_thread = threading.Thread(None, self.sre_server.run)
        self.server_thread.daemon = True
        self.server_thread.start()

    def stop(self):
        """ Stop the server thread """
        if self.sre_server is not None:
            self.sre_server.shutdown()
            self.server_thread.join()
            self.sre_server = None
            self.server_thread = None


class KeepAliveServer():
    """ Keep Alive Server for all SRE KeepAlive requests """
    # SRE Server vars
    uri = '127.0.0.1'
    port = 31646
    server = SREServer()
    ref_count = 0

    def add_ref(self):
        """ Add a reference count to the keep alive server and start if it is the first one """
        if KeepAliveServer.ref_count == 0:
            KeepAliveServer.server.run(KeepAliveServer.uri, KeepAliveServer.port)
        KeepAliveServer.ref_count += 1

    def remove_ref(self):
        """ Remove a reference count to the keep alive server and stop if it is the last one """
        KeepAliveServer.ref_count -= 1
        if KeepAliveServer.ref_count < 1:
            KeepAliveServer.server.stop()

        # sanity check
        if KeepAliveServer.ref_count < 0:
            print('Keep Alive Server ref count below zero')
            KeepAliveServer.ref_count = 0
