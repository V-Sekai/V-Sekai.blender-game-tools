import os
import pathlib

import addon_utils
import bpy

from . import arkit_shapes as shapes

RIG_FILE = '/resources/FaceitRig.blend'
CONTROL_RIG_FILE = '/resources/FaceitControlRig.blend'
LANDMARKS_FILE = '/resources/FaceitLandmarks.blend'
RETARGET_PRESETS = '/resources/retarget_presets/'
EXPRESSION_PRESETS = '/resources/expressions/'
EXPRESSION_PRESETS_RIGIFY_NEW = '/resources/expressions/new_rigify_rig/'

FACEIT_VERTEX_GROUPS = [
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
    'faceit_facial_hair',
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
    return get_addon_dir() + RETARGET_PRESETS


def get_expression_presets(rig_type='FACEIT'):
    '''Get the expressions presets folder for the rig type
    @rig_type: value in ['FACEIT', 'RIGIFY_NEW']
    '''
    if rig_type in ('FACEIT', 'RIGIFY'):
        return get_addon_dir() + EXPRESSION_PRESETS
    elif rig_type == 'RIGIFY_NEW':
        return get_addon_dir() + EXPRESSION_PRESETS_RIGIFY_NEW


def get_rig_file():
    return get_addon_dir() + RIG_FILE


def get_control_rig_file():
    return get_addon_dir() + CONTROL_RIG_FILE


def get_landmarks_file():
    return get_addon_dir() + LANDMARKS_FILE


def get_engine_settings(engine):
    if engine == 'FACECAP':
        engine_settings = bpy.context.scene.faceit_face_cap_mocap_settings
        engine_settings.indices_order = 'FACECAP'
    elif engine == 'EPIC':
        engine_settings = bpy.context.scene.faceit_epic_mocap_settings
        engine_settings.indices_order = 'ARKIT'
    elif engine == 'A2F':
        engine_settings = bpy.context.scene.faceit_a2f_mocap_settings
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


def get_a2f_shape_data():
    '''Returns list of the original arkit expression names'''
    return shapes.A2F['Data']


def get_tongue_shape_data():
    '''Returns list of the original arkit expression names'''
    return shapes.TONGUE['Data']


def get_phonemes_shape_data():
    '''Returns list of the original arkit expression names'''
    return shapes.PHONEMES['Data']


def get_rigify_bone_from_old_name(bone_name):
    RIGIFY_OLD_TO_NEW = {
        'lips.L': 'lip_end.L.001',
        'lips.R': 'lip_end.R.001',
        'tongue_master': 'tongue',
        'tongue': 'tweak_tongue',
        'tongue.001': 'tweak_tongue.001',
        'tongue.002': 'tweak_tongue.002',
        'tongue.003': 'tweak_tongue.003',
        'nose.005': 'nose_end.004',
        'chin.002': 'chin_end.001',
        'eyes': 'eye_common',
    }
    return RIGIFY_OLD_TO_NEW.get(bone_name, bone_name)


def get_shape_data_for_mocap_engine(mocap_engine=None):
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
    if mocap_engine == 'A2F':
        return get_a2f_shape_data()


def get_list_faceit_groups():

    return FACEIT_VERTEX_GROUPS


def get_face_region_items(self, context):
    ''' Returns the regions dictionary keys as enum items '''
    region_items = []
    for r in FACE_REGIONS_BASE.keys():
        region_items.append((r, r, r))
    return region_items


def get_regions_dict():
    region_dict = {}
    for region, shapes in FACE_REGIONS_BASE.items():
        for shape in shapes:
            region_dict[shape] = region

    return region_dict


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
        'eyesLookLeft',
        'eyesLookRight',
        'eyesLookUp',
        'eyesLookDown',
        'eyesCloseL',
        'eyesCloseR',
        'eyesUpperLidRaiserL',
        'eyesUpperLidRaiserR',
        'squintL',
        'squintR',
    ],
    'Brows': [
        'browDownLeft',
        'browDownRight',
        'browInnerUp',
        'browOuterUpLeft',
        'browOuterUpRight',
        'browLowerL',
        'browLowerR',
        'innerBrowRaiserL',
        'innerBrowRaiserR',
        'outerBrowRaiserL',
        'outerBrowRaiserR',
    ],
    'Cheeks': [
        'cheekPuff',
        'cheekSquintLeft',
        'cheekSquintRight',
        'cheekRaiserL',
        'cheekRaiserR',
        'cheekPuffL',
        'cheekPuffR',
    ],
    'Nose': [
        'noseSneerLeft',
        'noseSneerRight',
        'noseWrinklerL',
        'noseWrinklerR',
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
        'aa_ah_ax_01',
        'aa_02',
        'ao_03',
        'ey_eh_uh_04',
        'er_05',
        'y_iy_ih_ix_06',
        'w_uw_07',
        'ow_08',
        'aw_09',
        'oy_10',
        'ay_11',
        'h_12',
        'r_13',
        'l_14',
        's_z_15',
        'sh_ch_jh_zh_16',
        'th_dh_17',
        'f_v_18',
        'd_t_n_19',
        'k_g_ng_20',
        'p_b_m_21',
        'jawDrop',
        'jawDropLipTowards',
        'jawThrust',
        'jawSlideLeft',
        'jawSlideRight',
        'mouthSlideLeft',
        'mouthSlideRight',
        'dimplerL',
        'dimplerR',
        'lipCornerPullerL',
        'lipCornerPullerR',
        'lipCornerDepressorL',
        'lipCornerDepressorR',
        'lipStretcherL',
        'lipStretcherR',
        'upperLipRaiserL',
        'upperLipRaiserR',
        'lowerLipDepressorL',
        'lowerLipDepressorR',
        'chinRaiser',
        'lipPressor',
        'pucker',
        'funneler',
        'lipSuck',

    ],
    'Tongue': [
        'tongueOut',
        'tongueBack',
        'tongueTwistLeft',
        'tongueTwistRight',
        'tongueLeft',
        'tongueRight',
        'tongueWide',
        'tongueThin',
        'tongueCurlUp',
        'tongueCurlUp',
        'tongueCurlUp',
        'tongueCurlDown',
    ],
    'Other': [

    ]
}

FACEIT_BONES = [
    'MCH-eyes_parent', 'eyes', 'eye.L', 'eye.R', 'DEF-face', 'DEF-forehead.L', 'DEF-forehead.R', 'DEF-forehead.L.001',
    'DEF-forehead.R.001', 'DEF-forehead.L.002', 'DEF-forehead.R.002', 'DEF-temple.L', 'DEF-temple.R', 'master_eye.L',
    'brow.B.L', 'DEF-brow.B.L', 'brow.B.L.001', 'DEF-brow.B.L.001', 'brow.B.L.002', 'DEF-brow.B.L.002', 'brow.B.L.003',
    'DEF-brow.B.L.003', 'brow.B.L.004', 'lid.B.L', 'lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003', 'lid.T.L',
    'lid.T.L.001', 'lid.T.L.002', 'lid.T.L.003', 'MCH-eye.L', 'DEF_eye.L', 'MCH-eye.L.001', 'MCH-lid.B.L',
    'DEF-lid.B.L', 'MCH-lid.B.L.001', 'DEF-lid.B.L.001', 'MCH-lid.B.L.002', 'DEF-lid.B.L.002', 'MCH-lid.B.L.003',
    'DEF-lid.B.L.003', 'MCH-lid.T.L', 'DEF-lid.T.L', 'MCH-lid.T.L.001', 'DEF-lid.T.L.001', 'MCH-lid.T.L.002',
    'DEF-lid.T.L.002', 'MCH-lid.T.L.003', 'DEF-lid.T.L.003', 'master_eye.R', 'brow.B.R', 'DEF-brow.B.R', 'brow.B.R.001',
    'DEF-brow.B.R.001', 'brow.B.R.002', 'DEF-brow.B.R.002', 'brow.B.R.003', 'DEF-brow.B.R.003', 'brow.B.R.004',
    'lid.B.R', 'lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003', 'lid.T.R', 'lid.T.R.001', 'lid.T.R.002', 'lid.T.R.003',
    'MCH-eye.R', 'DEF_eye.R', 'MCH-eye.R.001', 'MCH-lid.B.R', 'DEF-lid.B.R', 'MCH-lid.B.R.001', 'DEF-lid.B.R.001',
    'MCH-lid.B.R.002', 'DEF-lid.B.R.002', 'MCH-lid.B.R.003', 'DEF-lid.B.R.003', 'MCH-lid.T.R', 'DEF-lid.T.R',
    'MCH-lid.T.R.001', 'DEF-lid.T.R.001', 'MCH-lid.T.R.002', 'DEF-lid.T.R.002', 'MCH-lid.T.R.003', 'DEF-lid.T.R.003',
    'jaw_master', 'chin', 'DEF-chin', 'chin.001', 'DEF-chin.001', 'chin.L', 'DEF-chin.L', 'chin.R', 'DEF-chin.R', 'jaw',
    'DEF-jaw', 'jaw.L.001', 'DEF-jaw.L.001', 'jaw.R.001', 'DEF-jaw.R.001', 'MCH-tongue.001', 'tongue.001',
    'DEF-tongue.001', 'MCH-tongue.002', 'tongue.002', 'DEF-tongue.002', 'tongue_master', 'tongue', 'DEF-tongue',
    'tongue.003', 'teeth.B', 'DEF-teeth.B', 'brow.T.L', 'DEF-cheek.T.L', 'DEF-brow.T.L', 'brow.T.L.001',
    'DEF-brow.T.L.001', 'brow.T.L.002', 'DEF-brow.T.L.002', 'brow.T.L.003', 'DEF-brow.T.L.003', 'brow.T.R',
    'DEF-cheek.T.R', 'DEF-brow.T.R', 'brow.T.R.001', 'DEF-brow.T.R.001', 'brow.T.R.002', 'DEF-brow.T.R.002',
    'brow.T.R.003', 'DEF-brow.T.R.003', 'jaw.L', 'DEF-jaw.L', 'jaw.R', 'DEF-jaw.R', 'nose', 'DEF-nose', 'nose.L',
    'DEF-nose.L', 'nose.R', 'DEF-nose.R', 'MCH-mouth_lock', 'MCH-jaw_master', 'lip.B', 'DEF-lip.B.L', 'DEF-lip.B.R',
    'chin.002', 'MCH-jaw_master.001', 'lip.B.L.001', 'DEF-lip.B.L.001', 'lip.B.R.001', 'DEF-lip.B.R.001',
    'MCH-jaw_master.002', 'cheek.B.L.001', 'DEF-cheek.B.L.001', 'cheek.B.R.001', 'DEF-cheek.B.R.001', 'lips.L',
    'DEF-cheek.B.L', 'lips.R', 'DEF-cheek.B.R', 'MCH-jaw_master.003', 'lip.T.L.001', 'DEF-lip.T.L.001', 'lip.T.R.001',
    'DEF-lip.T.R.001', 'lip.T', 'DEF-lip.T.L', 'DEF-lip.T.R', 'nose.005', 'MCH-jaw_master.004', 'nose_master',
    'nose.002', 'DEF-nose.002', 'nose.003', 'DEF-nose.003', 'nose.001', 'DEF-nose.001', 'nose.004', 'DEF-nose.004',
    'nose.L.001', 'DEF-nose.L.001', 'nose.R.001', 'DEF-nose.R.001', 'cheek.T.L.001', 'DEF-cheek.T.L.001',
    'cheek.T.R.001', 'DEF-cheek.T.R.001', 'DEF_forhead_01.L', 'DEF_forhead_02.L', 'DEF_forhead_03.L',
    'DEF_forhead_04.L', 'DEF_forhead_01.R', 'DEF_forhead_02.R', 'DEF_forhead_03.R', 'DEF_forhead_04.R', 'teeth.T',
    'DEF-teeth.T']

FACEIT_CTRL_BONES = [
    'eyes', 'eye.L', 'eye.R', 'brow.B.L', 'brow.B.L.001', 'brow.B.L.002', 'brow.B.L.003', 'brow.B.L.004', 'lid.B.L',
    'lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003', 'lid.T.L', 'lid.T.L.001', 'lid.T.L.002', 'lid.T.L.003', 'brow.B.R',
    'brow.B.R.001', 'brow.B.R.002', 'brow.B.R.003', 'brow.B.R.004', 'lid.B.R', 'lid.B.R.001', 'lid.B.R.002',
    'lid.B.R.003', 'lid.T.R', 'lid.T.R.001', 'lid.T.R.002', 'lid.T.R.003', 'jaw_master', 'chin', 'chin.001', 'chin.L',
    'chin.R', 'jaw', 'jaw.L.001', 'jaw.R.001', 'tongue.001', 'tongue.002', 'tongue_master', 'tongue', 'tongue.003',
    'teeth.B', 'brow.T.L', 'brow.T.L.001', 'brow.T.L.002', 'brow.T.L.003', 'brow.T.R', 'brow.T.R.001', 'brow.T.R.002',
    'brow.T.R.003', 'jaw.L', 'jaw.R', 'nose', 'nose.L', 'nose.R', 'lip.B', 'chin.002', 'lip.B.L.001', 'lip.B.R.001',
    'cheek.B.L.001', 'cheek.B.R.001', 'lips.L', 'lips.R', 'lip.T.L.001', 'lip.T.R.001', 'lip.T', 'nose.005',
    'nose_master', 'nose.002', 'nose.003', 'nose.001', 'nose.004', 'nose.L.001', 'nose.R.001', 'cheek.T.L.001',
    'cheek.T.R.001', 'teeth.T']

MOD_TYPE_ICON_DICT = {
    "DATA_TRANSFER": "MOD_DATA_TRANSFER",
    "MESH_CACHE": "MOD_MESHDEFORM",
    "MESH_SEQUENCE_CACHE": "MOD_MESHDEFORM",
    "NORMAL_EDIT": "MOD_NORMALEDIT",
    "WEIGHTED_NORMAL": "MOD_NORMALEDIT",
    "UV_PROJECT": "MOD_UVPROJECT",
    "UV_WARP": "MOD_UVPROJECT",
    "VERTEX_WEIGHT_EDIT": "MOD_VERTEX_WEIGHT",
    "VERTEX_WEIGHT_MIX": "MOD_VERTEX_WEIGHT",
    "VERTEX_WEIGHT_PROXIMITY": "MOD_VERTEX_WEIGHT",
    "ARRAY": "MOD_ARRAY",
    "BEVEL": "MOD_BEVEL",
    "BOOLEAN": "MOD_BOOLEAN",
    "BUILD": "MOD_BUILD",
    "DECIMATE": "MOD_DECIM",
    "EDGE_SPLIT": "MOD_EDGESPLIT",
    "NODES": "GEOMETRY_NODES",
    "MASK": "MOD_MASK",
    "MIRROR": "MOD_MIRROR",
    "MESH_TO_VOLUME": "VOLUME_DATA",
    "MULTIRES": "MOD_MULTIRES",
    "REMESH": "MOD_REMESH",
    "SCREW": "MOD_SCREW",
    "SKIN": "MOD_SKIN",
    "SOLIDIFY": "MOD_SOLIDIFY",
    "SUBSURF": "MOD_SUBSURF",
    "TRIANGULATE": "MOD_TRIANGULATE",
    "VOLUME_TO_MESH": "VOLUME_DATA",
    "WELD": "AUTOMERGE_OFF",
    "WIREFRAME": "MOD_WIREFRAME",
    "ARMATURE": "MOD_ARMATURE",
    "CAST": "MOD_CAST",
    "CURVE": "MOD_CURVE",
    "DISPLACE": "MOD_DISPLACE",
    "HOOK": "HOOK",
    "LAPLACIANDEFORM": "MOD_MESHDEFORM",
    "LATTICE": "MOD_LATTICE",
    "MESH_DEFORM": "MOD_MESHDEFORM",
    "SHRINKWRAP": "MOD_SHRINKWRAP",
    "SIMPLE_DEFORM": "MOD_SIMPLEDEFORM",
    "SMOOTH": "MOD_SMOOTH",
    "CORRECTIVE_SMOOTH": "MOD_SMOOTH",
    "LAPLACIANSMOOTH": "MOD_SMOOTH",
    "SURFACE_DEFORM": "MOD_MESHDEFORM",
    "WARP": "MOD_WARP",
    "WAVE": "MOD_WAVE",
    "VOLUME_DISPLACE": "VOLUME_DATA",
    "CLOTH": "MOD_CLOTH",
    "COLLISION": "MOD_PHYSICS",
    "DYNAMIC_PAINT": "MOD_DYNAMICPAINT",
    "EXPLODE": "MOD_EXPLODE",
    "FLUID": "MOD_FLUIDSIM",
    "OCEAN": "MOD_OCEAN",
    "PARTICLE_INSTANCE": "MOD_PARTICLE_INSTANCE",
    "PARTICLE_SYSTEM": "MOD_PARTICLES",
    "SOFT_BODY": "MOD_SOFT",
    "SURFACE": "MODIFIER",
}

BAKE_MOD_TYPES = [
    'ARMATURE', 'CAST', 'CURVE', 'DISPLACE', 'HOOK', 'LAPLACIANDEFORM', 'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP',
    'SIMPLE_DEFORM', 'SMOOTH', 'CORRECTIVE_SMOOTH', 'LAPLACIANSMOOTH', 'SURFACE_DEFORM', 'WARP', 'WAVE',
    'VOLUME_DISPLACE', 'DATA_TRANSFER', 'MESH_CACHE', 'MESH_SEQUENCE_CACHE', 'VERTEX_WEIGHT_EDIT', 'VERTEX_WEIGHT_MIX',
    'VERTEX_WEIGHT_PROXIMITY', 'CLOTH']

# HIDE_MOD_TYPES = ['SURFACE_DEFORM']
