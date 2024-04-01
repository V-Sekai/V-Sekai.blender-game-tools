
import socket
import time
from threading import Thread, Event

from ..core.faceit_data import get_face_cap_shape_data

from .decode_ifacialmocap import decode_ifacial_mocap
from .decode_live_link_face import decode_live_link_face
from .decode_face_cap_tile import decode_face_cap_tile

osc_queue = []
# Exit event handles when the thread is ended.
exit_event = Event()


class QueueManager:
    '''Parse and queue incoming osc messages with current timestamp.'''

    def queue_data(self, target, values):
        '''Queue the data with the current timestamp.'''
        global osc_queue
        # shapes: /W, values: [0.0, 0.0, 0.0, ...]
        # head rotation: /HR, values: [0.0, 0.0, 0.0, 0.0]
        # head translation: /HT, values: [0.0, 0.0, 0.0]
        # eye rotation: /ERL, values: [0.0, 0.0, 0.0, 0.0]
        # eye rotation right: /ERR, values: [0.0, 0.0, 0.0]
        osc_queue.append([self._get_timestamp(), target, values])

    def _get_timestamp(self):
        return time.time()

    def reset(self):
        '''Clear the OSC queue for the next stream.'''
        global osc_queue
        osc_queue.clear()


class Receiver:
    ''' Handle opening and closing of udp socket, Receive OSC messages and add to queue'''
    sock = None
    queue_mgr = None
    run_thread = None
    enabled = False
    shape_reference = []
    # engine in ['EPIC', FACECAP, TILE, IFacialMocap]
    engine = 'FACECAP'

    def __init__(self, queue_mgr):
        self.queue_mgr = queue_mgr

    def run(self):
        # Receive messages continuously. Run while the socket is open.
        while True:
            if exit_event.is_set():
                break
            if self.sock is None:
                time.sleep(0.1)
                print('thread is sleeping.')
                continue

            data = None
            try:
                data, _address = self.sock.recvfrom(1024)
            except BlockingIOError as e:
                print('Blocking error:', e)
            except AttributeError as e:
                print('Socket error:', e)
            except OSError as e:
                print('Packet error:', e.strerror)

            if data:
                try:
                    if self.engine in ('FACECAP', 'TILE', ):
                        target, value = decode_face_cap_tile(data)
                        self.queue_mgr.queue_data(target, value)
                    elif self.engine == 'EPIC':
                        data = decode_live_link_face(data)
                        if data is None:
                            continue
                        for target, value in data:
                            self.queue_mgr.queue_data(target, value)
                    else:
                        data = decode_ifacial_mocap(data, self.shape_reference)
                        if data is None:
                            continue
                        for target, value in data:
                            self.queue_mgr.queue_data(target, value)
                except ValueError as e:
                    print('Packet contained no data')
                    print(e)
                except KeyError as e:
                    print('KeyError:', e)

    def start(self, engine, address, port):
        ''' Open the socket, start the thread. '''
        self.engine = engine
        if self.engine == 'IFACIALMOCAP':
            self.shape_reference = [target_data['name'] for target_data in get_face_cap_shape_data().values()]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.bind((address, port))
        print(f'Start listening to OSC on Port {port}')
        # Start the thread
        exit_event.clear()
        self.run_thread = Thread(target=self.run)
        self.run_thread.start()
        self.enabled = True

    def stop(self):
        ''' Close the socket, end the thread. '''
        self.enabled = False
        if self.sock is not None:
            # Close the socket
            self.sock.close()
            self.sock = None
            # End the thread
            print("Stopped listening to OSC.")
        else:
            pass
        exit_event.set()
        if self.run_thread is not None:
            self.run_thread.join()
