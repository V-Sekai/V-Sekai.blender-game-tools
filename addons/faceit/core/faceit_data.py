import os
import bpy
import pathlib
import addon_utils
from . import arkit_shapes as shapes


#os.path.join(str(main_dir), "resources")
rig_file = '/resources/FaceitRig.blend'
control_rig_file = '/resources/FaceitControlRig.blend'
landmarks_file = '/resources/FaceitLandmarks.blend'
retarget_presets = '/resources/retarget_presets/'
expression_presets = '/resources/expressions/'

faceit_vertex_groups = [
    'faceit_right_eyeball',
    'faceit_left_eyeball',
    'faceit_left_eyes_other',
    'faceit_right_eyes_other',
    'faceit_upper_teeth',
    'faceit_lower_teeth',
    'faceit_tongue',
    'faceit_eyelashes',
    'faceit_rigid',
    'faceit_main',
]


def get_faceit_current_version():

    version = '2'
    # return version
    for mod in addon_utils.modules():
        if mod.bl_info.get("name") == 'FACEIT':
            version = '.'.join([str(x) for x in mod.bl_info.get('version')])
            break
    return version


def get_addon_dir():
    return str(pathlib.Path(os.path.dirname(__file__)).parent.resolve())


def get_retargeting_presets():
    return get_addon_dir()+retarget_presets


def get_expression_presets():
    return get_addon_dir()+expression_presets


def get_rig_file():
    return get_addon_dir()+rig_file


def get_control_rig_file():
    return get_addon_dir()+control_rig_file


def get_landmarks_file():
    return get_addon_dir()+landmarks_file


def get_engine_settings(engine):
    if engine == 'FACECAP':
        engine_settings = bpy.context.scene.faceit_face_cap_mocap_settings
        engine_settings.indices_order = 'FACECAP'
    elif engine == 'EPIC':
        engine_settings = bpy.context.scene.faceit_epic_mocap_settings
        engine_settings.indices_order = 'ARKIT'
    return engine_settings


def get_arkit_shape_data():
    '''Returns list of the original arkit expression names'''
    return shapes.ARKIT['Data']


def get_face_cap_shape_data():
    '''Returns list of the original arkit expression names'''
    return shapes.FACECAP['Data']


def get_epic_shape_data():
    '''Returns list of the original arkit expression names'''
    return shapes.EPIC['Data']


def get_shape_data_for_mocap_engine(mocap_engine=''):
    '''Takes the original expression name and returns the new index for the specified mocap engine
    @arkit_name: must be in ARKIT['Names']
    @mocap_engine: value in [ARKIT, FACECAP, EPIC]
    '''
    if not mocap_engine:
        return
    if mocap_engine == 'ARKIT':
        return get_arkit_shape_data()
    if mocap_engine == 'FACECAP':
        return get_face_cap_shape_data()
    if mocap_engine == 'EPIC':
        return get_epic_shape_data()


def get_list_faceit_groups():

    return faceit_vertex_groups


FACE_REGIONS_BASE = {
    'Eyes': [
        'eyeBlinkLeft',
        'eyeLookDownLeft',
        'eyeLookInLeft',
        'eyeLookOutLeft',
        'eyeLookUpLeft',
        'eyeSquintLeft',
        'eyeWideLeft',
        'eyeBlinkRight',
        'eyeLookDownRight',
        'eyeLookInRight',
        'eyeLookOutRight',
        'eyeLookUpRight',
        'eyeSquintRight',
        'eyeWideRight',
    ],
    'Brows': [
        'browDownLeft',
        'browDownRight',
        'browInnerUp',
        'browOuterUpLeft',
        'browOuterUpRight',
    ],
    'Cheeks': [
        'cheekPuff',
        'cheekSquintLeft',
        'cheekSquintRight',
    ],
    'Nose': [
        'noseSneerLeft',
        'noseSneerRight',
    ],
    'Mouth': [
        'jawForward',
        'jawLeft',
        'jawRight',
        'jawOpen',
        'mouthClose',
        'mouthFunnel',
        'mouthPucker',
        'mouthRight',
        'mouthLeft',
        'mouthSmileLeft',
        'mouthSmileRight',
        'mouthFrownRight',
        'mouthFrownLeft',
        'mouthDimpleLeft',
        'mouthDimpleRight',
        'mouthStretchLeft',
        'mouthStretchRight',
        'mouthRollLower',
        'mouthRollUpper',
        'mouthShrugLower',
        'mouthShrugUpper',
        'mouthPressLeft',
        'mouthPressRight',
        'mouthLowerDownLeft',
        'mouthLowerDownRight',
        'mouthUpperUpLeft',
        'mouthUpperUpRight',
    ],
    'Tongue': [
        'tongueOut',
    ],
    'Other': [

    ]
}
