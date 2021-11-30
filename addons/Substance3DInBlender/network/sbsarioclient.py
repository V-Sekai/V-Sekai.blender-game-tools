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


# Substance in Blender SBSAR IO Client
# 7/22/2020
import requests
from requests.exceptions import HTTPError
from .rest import make_threaded_requests, make_request
from .rest import RequestVerb
from .sreserver import KeepAliveServer
from .sreserver import SREHandler
from .sreclient import SREClient
from threading import Lock

SBSAR_ENDPOINT = "http://127.0.0.1:41646/v1/sbsar"
SBSAR_PORT = 31648
LOAD_TIMOUT_IN_SECONDS = 60


class SbsarRenderCallbackInterface():
    """ Resource render callback interface """
    def updateRender(self, data):
        pass


class SbsarRenderCallbackHandler(SREHandler):
    """ Resource render callback Handler """
    _listeners = []

    @classmethod
    def addListener(cls, listener):
        """ Register a render listener """
        cls._listeners.append(listener)

    @classmethod
    def removeListener(cls, listener):
        """ Unregister a render listener """
        try:
            cls._listeners.remove(listener)
        except Exception:
            pass

    def do_POST(self):
        """ REST Post action """
        if self.validateRequest(self.headers):
            content_len = int(self.headers.get('Content-Length'))
            data = self.rfile.read(content_len)

            # notify the listeners
            if data is not None:
                for listener in SbsarRenderCallbackHandler._listeners:
                    listener.updateRender(data)
            else:
                print('SbsarRenderCallbackHandler::do_Post has no data')

            # send the response after handling the data
            self._set_response(200)


class SbsarClient(SREClient):
    """ A REST Client for SBSAR data """

    def __init__(self):
        super().__init__()
        super().setup(SBSAR_ENDPOINT, SBSAR_PORT)

        # Keep isRendering thread safe
        self.isRenderingLock = Lock()

        # Is there a render request being processed
        self.isRendering = False

    def __del__(self):
        super().__del__()

    def isRenderQueued(self):
        """ Return true if rendering is already queued """
        with self.isRenderingLock:
            return self.isRendering

    def setRenderQueued(self, value):
        """ Acquire the rendering lock and set the is Rendering Value """
        with self.isRenderingLock:
            self.isRendering = value

    def sendFile(self, filepath):
        """ Send a file to the remote engine """
        keepAliveValue = "http://" + KeepAliveServer.uri + ':' + str(KeepAliveServer.port)
        renderCallbackUri = "http://" + KeepAliveServer.uri + ':' + str(SBSAR_PORT)
        data = {'path': filepath, 'keepAliveCallback': keepAliveValue,
                'renderCallback': renderCallbackUri, 'format': 'tga'}
        if self.session is None:
            self.session = requests.Session()
        output = make_request(self.session, RequestVerb.post, self.endpoint, data, LOAD_TIMOUT_IN_SECONDS)
        if isinstance(output, (Exception, HTTPError)):
            return 'Error: ' + str(output)
        elif output is not None:
            return output.json()['id']
        return ''

    def deleteSbsar(self, sbsarId):
        """ Delete an SBSAR resource """
        output_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarId)
        make_request(self.session, RequestVerb.delete, output_endpoint, LOAD_TIMOUT_IN_SECONDS)

    def duplicateSbsar(self, duplicateId):
        """ Send a file to the remote engine """
        output_endpoint = SBSAR_ENDPOINT + "/" + str(duplicateId) + "/duplicate"
        output = make_request(self.session, RequestVerb.post, output_endpoint, LOAD_TIMOUT_IN_SECONDS)
        if isinstance(output, (Exception, HTTPError)):
            return 'Error: ' + str(output)
        elif output is not None:
            return output.json()['id']
        return ''

    def getAllParams(self, sbsarid):
        """ Query all of the parameters for the given SBSAR ID """
        parameter_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/parameters"
        response = self.request(parameter_endpoint, RequestVerb.get)
        return self.getResponseData(response, 'parameters')

    def queryAllOutputs(self, sbsarid):
        """ Query all of the outputs for the given SBSAR ID """
        output_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/outputs"
        response = self.request(output_endpoint, RequestVerb.get)
        return self.getResponseData(response, 'outputs')

    def getResponseData(self, response, value):
        """ Validate the response and fixup the output """
        if response is None or isinstance(response, HTTPError):
            return 'ERROR', None
        elif isinstance(response, Exception):
            if 'timed out' in str(response):
                return 'ERROR - timed out', None
            else:
                return 'ERROR', None
        else:
            try:
                rjson = response.json()
                if rjson and rjson[value]:
                    return 'SUCCESS', rjson[value]
                else:
                    return 'SUCCESS', None
            except Exception:
                return 'ERROR', None

    def sendParamUpdate(self, sbsarid, paramId, value, threaded):
        """ Update parameter paramID of SBSAR id with data """
        output_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/parameter/" + str(paramId)
        if isinstance(value, bool):
            data = {'value': int(value)}
        elif hasattr(value, '__len__') and not isinstance(value, str):
            data = {'value': list(value)}
        else:
            data = {'value': value}

        # if threaded send a render call with it
        if threaded:
            reqs = []
            reqs.append((output_endpoint, RequestVerb.patch, data))
            render_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/render"
            if not self.isRenderQueued():
                self.setRenderQueued(True)
                reqs.append((render_endpoint, RequestVerb.patch, {}))
            make_threaded_requests(self.session, reqs)
        else:
            return self.request(output_endpoint, RequestVerb.patch, data)

    def render(self, sbsarid):
        """ Signal the remote engine to render a specific SBSAR """
        self.setRenderQueued(True)
        output_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/render"
        return self.request(output_endpoint, RequestVerb.patch)

    def savePreset(self, sbsarid):
        """ Save the current set of parameters as a preset """
        output_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/presets"
        return self.request(output_endpoint, RequestVerb.get)

    def loadPreset(self, sbsarid, presetData, index):
        """ Load a parameter preset """
        data = {'preset': presetData}
        output_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/preset/" + str(index)
        return self.request(output_endpoint, RequestVerb.patch, data)

    def getEmbeddedPresets(self, sbsarid):
        """ Retrieve a list of embedded presets for this resource """

        #  Currently only graph 0 is supported
        output_endpoint = SBSAR_ENDPOINT + "/" + str(sbsarid) + "/embeddedpresets/0"
        response = self.request(output_endpoint, RequestVerb.get)
        return self.getResponseData(response, 'embeddedpresets')

    def request(self, endpoint, request_verb, data={}):
        """ Make a SBSAR REST request to the remote engine """
        if self.session is None:
            self.session = requests.Session()
        return make_request(self.session, request_verb, endpoint, data)
