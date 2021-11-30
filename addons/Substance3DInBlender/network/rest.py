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


# Substance in Blender Rest Requests
# 7/22/2020
import requests
import threading
from enum import Enum
from requests.exceptions import HTTPError
from time import time, sleep


def get_current_time_in_ms():
    """ Get current time in MS """
    return int(round(time() * 1000))


REQUEST_TIMEOUT_IN_SECONDS = 10
MAX_RETRIES = 3
THREADED_THROTTLE_IN_MS = 5
NEXT_THREAD_STARTTIME = get_current_time_in_ms() + THREADED_THROTTLE_IN_MS


# currently supported http requests
class RequestVerb(Enum):
    """ Possible Reqeust actions """
    post = 1
    delete = 2
    put = 3
    patch = 4
    get = 5


def make_threaded_requests(session, reqs):
    """ Send the requests on a thread when the return value isn't needed """
    global NEXT_THREAD_STARTTIME
    throttleTimeMs = 0
    curr_millis = get_current_time_in_ms()
    if curr_millis > NEXT_THREAD_STARTTIME:
        NEXT_THREAD_STARTTIME = curr_millis + THREADED_THROTTLE_IN_MS
    else:
        throttleTimeMs = NEXT_THREAD_STARTTIME - curr_millis
        NEXT_THREAD_STARTTIME = NEXT_THREAD_STARTTIME + THREADED_THROTTLE_IN_MS

    threading.Thread(target=process_threaded_requests, args=(session, reqs, throttleTimeMs/1000)).start()


def process_threaded_requests(session, requests, sleepTimeS):
    """ Send requests from this thread """

    # Throttle if needed
    if sleepTimeS > 0:
        sleep(sleepTimeS)

    # send the request
    for r in requests:
        response = make_request(session, r[1], r[0], r[2])
        if response is None or isinstance(response, (Exception, HTTPError)):
            print('Threaded request fail: ' + str(r[0]))


def make_request(session, verb, endpoint, data={},
                 timeoutInSeconds=REQUEST_TIMEOUT_IN_SECONDS,
                 max_retries=MAX_RETRIES):
    """ Make a REST request """
    try:
        if verb is RequestVerb.post:
            r = session.post(url=endpoint, json=data, timeout=timeoutInSeconds)
            if r.status_code == requests.codes.ok or r.status_code == requests.codes.created:
                return r
            else:
                print('Error: ' + str(r.status_code) + ' Posting to Endpoint: ' + str(endpoint))
                return None
        elif verb is RequestVerb.delete:
            r = session.delete(url=endpoint, timeout=timeoutInSeconds)
            if r.status_code == requests.codes.ok:
                return r
            else:
                print('Error: ' + str(r.status_code) + ' Deleting Endpoint: ' + str(endpoint))
                return None
        elif verb is RequestVerb.put:
            r = session.put(url=endpoint, json=data, timeout=timeoutInSeconds)
            if r.status_code == requests.codes.ok:
                return r
            else:
                print('Error: ' + str(r.status_code) + ' Putting Endpoint: ' + str(endpoint))
                return None
        elif verb is RequestVerb.patch:
            r = session.patch(url=endpoint, json=data, timeout=timeoutInSeconds)
            if r.status_code == requests.codes.ok or r.status_code == requests.codes.no_content:
                return r
            else:
                print('Error: ' + str(r.status_code) + ' Patching Endpoint: ' + str(endpoint))
                return None
        elif verb is RequestVerb.get:
            r = session.get(url=endpoint, timeout=timeoutInSeconds)
            if r.status_code == requests.codes.ok or r.status_code == requests.codes.no_content:
                return r
            else:
                print('Error: ' + str(r.status_code) + ' Getting Endpoint: ' + str(endpoint))
                return None
        else:
            print('Make request verb not supported: ' + str(verb))
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err} Request Verb: {str(verb)} Endpoint: {str(endpoint)}')
        return http_err
    except requests.ConnectionError as err:
        if max_retries > 0:
            max_retries = max_retries - 1
            sleep(0.25)
            return make_request(session, verb, endpoint, data, timeoutInSeconds, max_retries)
        else:
            print('Connection Error, will not retry')
            return err
    except Exception as err:
        print(f'Other error occurred: {err}' + ' Request Verb: ' + str(verb) + ' Endpoint: ' + str(endpoint))
        return err
