import bpy
import csv
import json

from .mocap_base import MocapBase
from ..core.faceit_data import get_face_cap_shape_data, get_epic_shape_data, get_a2f_shape_data
from ..core.shape_key_utils import set_slider_max


class FaceCapImporter(MocapBase):

    def _initialize_mocap_settings(self):
        self.set_rotation_units('DEG')
        self.set_source_shape_reference(list(get_face_cap_shape_data().keys()))
        # self.shape_ref = list(get_face_cap_shape_data().keys())

    def parse_animation_data(self, data, frame_start=0, record_frame_rate=1000):
        self.clear_animation_data()
        with open(data) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not row:
                    continue
                if row[0] != 'k':
                    continue
                # Nano seconds since last frame
                current_frame = frame_start + (float(row[1]) / record_frame_rate) * self.fps
                self.animation_timestamps.append(current_frame)
                if self.animate_head_rotation:
                    self.head_rot_animation_lists.append([float(v) for v in row[5:8]])
                if self.animate_head_location:
                    self.head_loc_animation_lists.append([float(v) for v in row[2:5]])
                # Eyes Motion
                if self.aniamte_eyes:
                    self.eye_L_animation_lists.append([float(v) for v in row[8:10]])
                    self.eye_R_animation_lists.append([float(v) for v in row[10:12]])
                # Blendshapes Motion
                if self.animate_shapes:
                    self.sk_animation_lists.append([float(v) for v in row[12:]])

        # initialize the first frame location offset
        if self.animate_head_location and self.head_loc_animation_lists:
            self._get_initial_location_offset(self.head_loc_animation_lists[0])


class A2FMocapImporter(MocapBase):

    def _initialize_mocap_settings(self):
        self.set_source_shape_reference(list(get_a2f_shape_data().keys()))
        # self.shape_ref = list(get_a2f_shape_data().keys())

    def parse_animation_data(self, data, frame_start=0, record_frame_rate=60):
        self.clear_animation_data()
        with open(data, 'r') as f:
            data = json.load(f)
            for i, shape_key_values in enumerate(data['weightMat']):
                if shape_key_values is None:
                    continue
                current_frame = frame_start + i * self.fps / record_frame_rate
                self.animation_timestamps.append(current_frame)
                # Blendshapes Motion
                if self.animate_shapes:
                    self.sk_animation_lists.append([float(v) for v in shape_key_values])


class EpicMocapImporter(MocapBase):

    def _initialize_mocap_settings(self):
        self.set_rotation_units('RAD')
        self.set_source_shape_reference(list(get_epic_shape_data().keys()))
        # self.shape_ref = list(get_epic_shape_data().keys())

    def parse_animation_data(self, data, frame_start=0, record_frame_rate=60):
        self.clear_animation_data()
        first_frame = None
        with open(data) as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if not row:
                    continue
                if i == 0:
                    continue
                if float(row[1]) == 0:
                    # No values in this frame
                    continue
                if first_frame is None:
                    first_frame = self._convert_timecode_to_frames(row[0], self.fps, record_frame_rate) - frame_start
                self.animation_timestamps.append(self._convert_timecode_to_frames(
                    row[0], self.fps, record_frame_rate) - first_frame)

                # Blendshapes Motion
                if self.animate_shapes:
                    self.sk_animation_lists.append([float(v) for v in row[2:54]])
                # Head Motion
                if self.animate_head_rotation:
                    self.head_rot_animation_lists.append([float(v) for v in row[54:57]])
                # Eyes Motion
                if self.aniamte_eyes:
                    self.eye_L_animation_lists.append([float(v) for v in row[57:60]])
                    self.eye_R_animation_lists.append([float(v) for v in row[60:63]])

    def _convert_timecode_to_frames(self, timecode, framerate, start=None, recorded_framerate=60):
        '''This function converts an SMPTE timecode into frames
        @timecode [str]: format hh:mm:ss:ff
        @start [str]: optional timecode to start at
        '''
        def _seconds(value):
            '''convert value to seconds
            @value [str, int, float]: either timecode or frames
            '''
            if isinstance(value, str):  # value seems to be a timestamp
                _zip_ft = zip((3600, 60, 1, 1 / recorded_framerate), value.split(':'))
                return sum(f * float(t) for f, t in _zip_ft)
            elif isinstance(value, (int, float)):  # frames
                return value / framerate
            else:
                return 0

        def _frames(seconds):
            '''convert seconds to frames
            @seconds [int]: the number of seconds
            '''
            return seconds * framerate

        return _frames(_seconds(timecode) - _seconds(start))


class OSCLiveAnimator(MocapBase):
    '''Animate the target values live and populate animations from recorded data.'''
    # TILE, FC
    osc_source_engine = 'FC'

    def _initialize_mocap_settings(self):
        self.set_source_shape_reference(list(get_face_cap_shape_data().keys()))
        # self.shape_ref = list(get_face_cap_shape_data().keys())

    def init_new_recording(self):
        self.initial_location_offset = None
        self.head_bone = None
        self.head_action = None
        self.head_obj = None

    def process_data(self, data):
        _timestamp, address, params = data
        if self.animate_shapes and address == '/W':
            value = params[1]
            name = self.source_shape_reference[params[0]]
            self._set_shape_key_values(name, value)
        elif self.animate_head_rotation and address == '/HR':  # head rotation.
            self._set_head_rotation(params)
        elif self.animate_head_location and address == '/HT':  # Head translation.
            if not self.initial_location_offset:
                self._get_initial_location_offset(params)
            # else:
            self._set_head_location(params)

    def _set_shape_key_values(self, name, value):
        '''Animate the specified shape key on all registered objects'''
        target_shapes = self.target_shapes_dict[name]
        amplify = self.retarget_shapes[name].amplify
        for sk in target_shapes:
            val = value * amplify
            # if self.dynamic_sk_ranges:
            #     set_slider_max(sk, val)
            # set_slider_min(sk, )
            sk.value = val

    def _set_head_rotation(self, value):
        obj = self.head_obj
        if obj:
            new_rot = self._rotation_to_blender(value)
            if self.head_bone:
                setattr(self.head_bone, self.head_rotation_data_path, new_rot)
            else:
                setattr(obj, self.head_rotation_data_path, new_rot)

    def _set_head_location(self, value):
        obj = self.head_obj
        if obj:
            new_loc = self.initial_location_offset + self._location_to_blender(value)
            if self.head_bone:
                self.head_bone.location = new_loc
            else:
                obj.location = new_loc

    def parse_animation_data(self, data, frame_start=0, record_frame_rate=1000):
        '''Parse the recorded messages into readable animation data'''
        if not data:
            return
        self.clear_animation_data()

        shape_key_values = []
        timestamp = None
        first_timestamp = None

        shape_idx = 0
        last_shape_idx = 0
        frame_number = 0
        missing_frames = []

        # Collect shape data and timestamps
        for i, frame_data in enumerate(data):
            _time, _address, _value = frame_data
            if first_timestamp is None:
                first_timestamp = _time
            if _address == "/W":
                shape_idx = _value[0]
                if shape_idx < last_shape_idx:
                    # New Frame
                    if len(shape_key_values) == 52:
                        self.animation_timestamps.append(timestamp)
                        self.sk_animation_lists.append([v[1] for v in shape_key_values])
                    else:
                        missing_frames.append(frame_number)
                        print(f"frame {frame_number} not complete. Found only {len(shape_key_values)} expression values.")

                    timestamp = None
                    shape_key_values = []

            if timestamp is None:
                timestamp = (_time - first_timestamp) * self.fps + frame_start
            if _address == "/W":
                shape_key_values.append(_value)

            frame_number += 1
            last_shape_idx = shape_idx

        hr = [x[2] for x in data if x[1] == "/HR"]
        ht = [x[2] for x in data if x[1] == "/HT"]
        elr = [x[2] for x in data if x[1] == "/ELR"]
        err = [x[2] for x in data if x[1] == "/ERR"]

        self.head_rot_animation_lists = [x for i, x in enumerate(hr) if i not in missing_frames]
        self.head_loc_animation_lists = [x for i, x in enumerate(ht) if i not in missing_frames]
        self.eye_L_animation_lists = [x for i, x in enumerate(elr) if i not in missing_frames]
        self.eye_R_animation_lists = [x for i, x in enumerate(err) if i not in missing_frames]

        # print(len(self.animation_timestamps))
        # print(len(self.eye_L_animation_lists))
        # print(len(self.eye_R_animation_lists))
        # print(len(self.head_rot_animation_lists))
        # print(len(self.head_loc_animation_lists))
        # self.left_eye_rot_animation_lists = [x[2] for x in data if x[1] == "/ELL"]
        # self.right_eye_rot_animation_lists = [x[2] for x in data if x[1] == "/ELR"]

    @ staticmethod
    def _get_mean_timestamp(timestamps):
        # timestamps = [lst[0] for lst in data]
        return sum(timestamps) / len(timestamps)
