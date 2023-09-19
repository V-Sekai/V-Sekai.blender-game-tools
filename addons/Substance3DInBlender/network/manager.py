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

# file: network/manager.py
# brief: Network operations manager
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2


from .server import SRE_Server
from ..common import Code_Response


class SUBSTANCE_ServerManager():
    def __init__(self):
        self.server = SRE_Server()

    # SERVER
    def server_start(self):
        if not self.server.is_running():
            return self.server.start()
        else:
            return Code_Response.server_already_running_error

    def server_port(self):
        if self.server.is_running():
            return (Code_Response.success, self.server.get_port())
        else:
            return (Code_Response.server_not_running_error, None)

    def server_stop(self):
        if self.server.is_running():
            return self.server.stop()
        else:
            return Code_Response.server_not_running_error

    def server_send_message(self, type, verb, endpoint, data={}, ignore_connection_error=False):
        if self.server.is_running():
            return self.server.send_message(
                type,
                verb,
                endpoint,
                data=data,
                ignore_connection_error=ignore_connection_error)
        else:
            return (Code_Response.server_not_running_error, None)
