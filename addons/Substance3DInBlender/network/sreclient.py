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


# Substance in Blender SRE Client
# 7/22/2020
from .rest import make_request, RequestVerb
from .sreserver import SREServer, KeepAliveServer, SREHandler


class SREClient():
    """ Base class for any client of the remote engine """
    def __init__(self):
        self.servers_running = False
        self.id = {}
        self.data = {}
        self.render_callback_server = SREServer()
        self.keepalive_server = KeepAliveServer()
        self.session = None

    def __del__(self):
        self.stopServers()

    def setup(self, endoint, callback_port):
        """ Assign the endpoint and callback port for this client """
        self.endpoint = endoint
        self.rendercallback_port = callback_port

    def stopServers(self):
        """ Shutdown this client """
        # Unregister with SRE
        if self.servers_running:
            if 'id' in self.id and len(self.id['id']) > 0 and len(self.endpoint) > 0:
                make_request(self.session, RequestVerb.delete, self.endpoint + "/" + self.id['id'])
            self.id = {}

            # Stop SRE communication servers
            self.session = None
            self.render_callback_server.stop()
            self.keepalive_server.remove_ref()
            self.servers_running = False

    def connect(self, handler=SREHandler):
        """ Connect this client to the remote engine """
        # Start SRE communication servers
        if not self.servers_running:
            self.servers_running = True
            self.keepalive_server.add_ref()
            self.render_callback_server.run(self.keepalive_server.uri, self.rendercallback_port, handler)
        return True
