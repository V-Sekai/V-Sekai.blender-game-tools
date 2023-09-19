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

# file: network/rest.py
# brief: Rest requests
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import traceback
import requests
import threading
from requests.exceptions import HTTPError
from time import sleep

from ..utils import SUBSTANCE_Utils
from ..common import (
    Code_RequestVerb,
    Code_Response,
    REST_TIMEOUT_S,
    REST_MAX_TRIES,
    REST_THREAD_THROTTLE_MS
)


class SRE_Rest():
    def __init__(self):
        self.next_thread_start = SUBSTANCE_Utils.get_current_time_in_ms() + REST_THREAD_THROTTLE_MS

    def async_request(self, session, verb, endpoint, data={}, ignore_connection_error=False):
        _throttle_ms = 0
        _current_ms = SUBSTANCE_Utils.get_current_time_in_ms()
        if _current_ms > self.next_thread_start:
            self.next_thread_start = _current_ms + REST_THREAD_THROTTLE_MS
        else:
            _throttle_ms = self.next_thread_start - _current_ms
            self.next_thread_start = self.next_thread_start + REST_THREAD_THROTTLE_MS

        threading.Thread(
            target=self._process_threaded_request,
            args=(session, verb, endpoint, data, ignore_connection_error, _throttle_ms/1000)).start()

    def _process_threaded_request(self, session, verb, endpoint, data={}, ignore_connection_error=False, throttle=0):
        if throttle > 0:
            sleep(throttle)
        _result = self.sync_request(session, verb, endpoint, data=data, ignore_connection_error=ignore_connection_error)
        if _result[0] is not Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Threaded request fail: {}".format(_result, endpoint))

    def sync_request(
            self,
            session,
            verb,
            endpoint,
            data={},
            ignore_connection_error=False,
            timeout_s=REST_TIMEOUT_S,
            max_retries=REST_MAX_TRIES):
        try:
            if verb is Code_RequestVerb.post:
                _r = session.post(url=endpoint, json=data, timeout=timeout_s)
                if _r.status_code == requests.codes.ok or _r.status_code == requests.codes.created:
                    return (Code_Response.success, _r)
                else:
                    return (Code_Response.rest_post_error, endpoint)
            elif verb is Code_RequestVerb.delete:
                _r = session.delete(url=endpoint, timeout=timeout_s)
                if _r.status_code == requests.codes.ok:
                    return (Code_Response.success, _r)
                else:
                    return (Code_Response.rest_delete_error, endpoint)
            elif verb is Code_RequestVerb.put:
                _r = session.put(url=endpoint, json=data, timeout=timeout_s)
                if _r.status_code == requests.codes.ok:
                    return (Code_Response.success, _r)
                else:
                    return (Code_Response.rest_put_error, endpoint)
            elif verb is Code_RequestVerb.patch:
                _r = session.patch(url=endpoint, json=data, timeout=timeout_s)
                if _r.status_code == requests.codes.ok or _r.status_code == requests.codes.no_content:
                    return (Code_Response.success, _r)
                else:
                    return (Code_Response.rest_patch_error, endpoint)
            elif verb is Code_RequestVerb.get:
                _r = session.get(url=endpoint, timeout=timeout_s)
                if _r.status_code == requests.codes.ok or _r.status_code == requests.codes.no_content:
                    return (Code_Response.success, _r)
                else:
                    return (Code_Response.rest_get_error, endpoint)
            else:
                return (Code_Response.rest_verb_error, endpoint)
        except HTTPError:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Rest HTTP error: {}".format(endpoint))
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.rest_http_error, endpoint)
        except requests.ConnectionError:
            if ignore_connection_error:
                SUBSTANCE_Utils.log_data("ERROR", "Exception - Rest Ignore Connection error: {}".format(endpoint))
                # SUBSTANCE_Utils.log_traceback(traceback.format_exc())
                return (Code_Response.rest_ignore_connection_error, endpoint)
            elif max_retries > 0:
                max_retries = max_retries - 1
                sleep(0.25)
                return self.sync_request(session, verb, endpoint, data, timeout_s, max_retries, ignore_connection_error)
            else:
                SUBSTANCE_Utils.log_data("ERROR", "Exception - Rest connection error: {}".format(endpoint))
                SUBSTANCE_Utils.log_traceback(traceback.format_exc())
                return (Code_Response.rest_connection_error, endpoint)
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Rest unknown error: {}".format(endpoint))
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.rest_unknown_error, endpoint)
