
import bpy
import numpy as np
from ..core.fc_dr_utils import kf_data_to_numpy_array, populate_keyframe_points_from_np_array
from datetime import datetime


def get_current_timestamp():
    '''Returns the current timestamp as a string.'''
    timeObj = datetime.now()
    return timeObj.strftime("%H:%M:%S.%f")


def get_scene_frame_rate():
    '''Returns the current framerate'''
    return bpy.context.scene.render.fps / bpy.context.scene.render.fps_base


def add_zero_keyframe(fcurves, frame) -> None:
    for fc in fcurves:
        fc.keyframe_points.insert(frame, 0.0, options={'FAST'})


def remove_frame_range(action, fcurves, frame_start, frame_end) -> None:
    '''Remove all keyframes from fcurves inbetween frame_start and frame_end'''
    remove_first_frames = False
    # Workaround for numpy bug, masking doesn't work when frame_start == 0
    if frame_start == 0:
        remove_first_frames = True
        frame_start = 2

    for fc in fcurves:

        kf_data = kf_data_to_numpy_array(fc)
        mask = ((kf_data < frame_start) | (kf_data > frame_end)).all(axis=1)

        if np.all(mask == 1):
            continue
        elif not np.any(mask == 1):
            action.fcurves.remove(fc)
            continue

        # Mask out overlapping frame range from existing fcurves
        dp = fc.data_path
        action.fcurves.remove(fc)
        fc = action.fcurves.new(dp)

        kf_data = kf_data[mask, :]
        if remove_first_frames:
            kf_data = np.delete(kf_data, [0, 1], axis=0)

        populate_keyframe_points_from_np_array(
            fc, kf_data, add=True)

        if remove_first_frames:
            # Remove keyframes that are not covered by mask
            # For some reason Blender doesn't always remove all kf -> range(3) for safety
            for _ in range(3):
                for kf in fc.keyframe_points:
                    frame = kf.co.x
                    if 0 <= frame <= frame_end:
                        fc.keyframe_points.remove(kf)


def get_action(self, action_name):
    '''
    Get an action by name, create it if it does not exist
    '''
    action = bpy.data.actions.get(action_name)
    if not action:
        self.report({'INFO'}, f'Creating new Action with name {action_name}')
        action = bpy.data.actions.new(name=action_name)
    return action
