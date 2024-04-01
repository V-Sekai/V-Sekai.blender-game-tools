
import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty, PointerProperty
import numpy as np

from ..core.retarget_list_base import FaceRegionsBase, FaceRegionsBaseProperties
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


def moving_average_filter(data, window_size):
    window = np.ones(int(window_size)) / float(window_size)
    return np.convolve(data, window, 'same')


def median_filter(data, kernel_size=3):
    # Handle edge cases by reflecting the data at the borders
    extended_data = np.pad(data, (kernel_size // 2, kernel_size // 2), 'reflect')
    smoothed_data = np.copy(data)

    for i in range(len(data)):
        # Take a window of data centered at the current point
        window = extended_data[i:i + kernel_size]
        # Replace the current value with the median of the window
        smoothed_data[i] = np.median(window)
    return smoothed_data


def gaussian_kernel(size, sigma):
    """ Returns a 1D Gaussian kernel. """
    size = int(size) // 2
    x = np.arange(-size, size + 1)
    norm = 1 / (np.sqrt(2 * np.pi) * sigma)
    g = np.exp(-x**2 / (2 * sigma**2)) * norm
    return g


def gaussian_filter1d(data, size, sigma):
    """ Applies a 1D Gaussian filter to a data array. """
    kernel = gaussian_kernel(size, sigma)
    # Convolve the data with the kernel using the 'valid' mode to avoid introducing artifacts
    return np.convolve(data, kernel, mode='same')


def remap(value, A, B, C, D):
    # Linearly remaps a value from the range [A, B] to the range [C, D]
    return C + (value - A) * (D - C) / (B - A)


class SmoothBaseProperties():
    '''Base Properties for the Smooth operation on all mocap operators.'''
    # use_smoothing: BoolProperty(
    #     name='Use Smoothing',
    #     description='If enabled the mocap data will be smoothed',
    #     default=False,
    # )
    # Face Settings
    use_smooth_face_filter: BoolProperty(
        name="Smooth Face Regions",
        default=False,
    )
    smooth_regions: PointerProperty(
        name='Smooth Regions',
        type=FaceRegionsBase,
        override={'LIBRARY_OVERRIDABLE'},
    )
    smoothing_filter_face: EnumProperty(
        name='Face Filter',
        items=(('SMA', 'Moving Average',
                'A moving average filter replaces each data point with the average of neighboring data points within the defined window size.'),
               ('MEDIAN', 'Median',
                'A Gaussian filter can be applied for smoothing, and it has the advantage of preserving features better than a simple moving average.'),
               ('GAUSSIAN', 'Gaussian',
                'A Gaussian filter can be applied for smoothing, and it has the advantage of preserving features better than a simple moving average.'),
               ),
        default='SMA'
    )
    smooth_window_face: IntProperty(
        name='Smooth Factor',
        default=3,
        min=1,
        max=100,
        description='Determines the kernel size for the smooth operation.',
    )
    # Head Settings
    smooth_head: BoolProperty(
        name='Smooth Head Motion',
        default=False,
    )
    smoothing_filter_head: EnumProperty(
        name='Head Filter',
        items=(('SMA', 'Moving Average',
                'A moving average filter replaces each data point with the average of neighboring data points within the defined window size.'),
               ('MEDIAN', 'Median',
                'A Gaussian filter can be applied for smoothing, and it has the advantage of preserving features better than a simple moving average.'),
               ('GAUSSIAN', 'Gaussian',
                'A Gaussian filter can be applied for smoothing, and it has the advantage of preserving features better than a simple moving average.'),
               ),
        default='SMA'
    )
    smooth_window_head: IntProperty(
        name='Smooth Factor',
        default=3,
        min=2,
        max=100,
        description='Determines the kernel size for the smooth operation.',
    )

    smooth_eye_look_animation: BoolProperty(
        name='Smooth Eye Motion',
        default=False,
    )
    smoothing_filter_eye_bones: EnumProperty(
        name='Eyes Filter',
        items=(('SMA', 'Moving Average',
                'A moving average filter replaces each data point with the average of neighboring data points within the defined window size.'),
               ('MEDIAN', 'Median',
                'A Gaussian filter can be applied for smoothing, and it has the advantage of preserving features better than a simple moving average.'),
               ('GAUSSIAN', 'Gaussian',
                'A Gaussian filter can be applied for smoothing, and it has the advantage of preserving features better than a simple moving average.'),
               ),
        default='SMA'
    )
    smooth_window_eye_bones: IntProperty(
        name='Smooth Factor',
        default=3,
        min=2,
        max=100,
        description='Determines the kernel size for the smooth operation.',
    )
