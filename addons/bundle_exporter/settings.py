import os
import bpy

prefix_copy = "__EXPORT_PREFIX_"

mesh_types = {'MESH', 'FONT', 'CURVE'}
empty_types = {'EMPTY'}
armature_types = {'ARMATURE'}

engines = [
    ('UNREAL', 'Unreal', 'Unreal Engine'),
    #('UNITY', 'Unity', 'Unity')
]

export_formats = [('FBX', 'FBX', 'fbx format'),
                  ('COLLADA', 'Collada ', 'collada format'),
                  ('GLTF', 'GLTF', 'gltf export'),
                  ('OBJ', 'OBJ', 'obj export')]

export_format_extensions = {'FBX': 'fbx',
                            'COLLADA': 'dae',
                            'GLTF': 'gltf',
                            'OBJ': 'obj'}

export_operators = {'FBX': bpy.ops.export_scene.fbx,
                    'COLLADA': bpy.ops.wm.collada_export,
                    'GLTF': bpy.ops.export_scene.gltf,
                    'OBJ': bpy.ops.export_scene.obj}

preset_folders = {'FBX': 'operator/export_scene.fbx/',
                  'OBJ': 'operator/export_scene.obj/',
                  'COLLADA': 'operator/wm.collada_export/',
                  'GLTF': 'operator/export_scene.gltf/'}

bge_presets_path = os.path.join(os.path.dirname(__file__), 'presets')

BGE_export_presets = {'FBX': {os.path.join(bge_presets_path, 'BGE_unreal.py'), os.path.join(bge_presets_path, 'BGE_unity.py'), os.path.join(bge_presets_path, 'BGE_unity_experimental.py')},
                      'OBJ': {os.path.join(bge_presets_path, 'BGE_obj.py')},
                      'COLLADA': {os.path.join(bge_presets_path, 'BGE_collada.py')},
                      'GLTF': {os.path.join(bge_presets_path, 'BGE_gltf.py')}}


def get_preset_files(export_format):
    for x in BGE_export_presets[export_format]:
        if os.path.isfile(x):
            yield os.path.split(x)[1][:-3], x
    paths = bpy.utils.preset_paths(preset_folders[export_format])
    for x in paths:
        for file in os.listdir(x):
            if file.endswith('.py') and file != '__init__.py':
                yield file[:-3], os.path.abspath(os.path.join(x, file))


# https://blender.stackexchange.com/questions/80956/load-and-update-enum-values
def get_presets(export_format):
    return {x[0]: x[1] for x in get_preset_files(export_format)}


def create_preset_enum(presets):
    presets = [(x, x, 'preset ' + x) for index, x in enumerate(presets.keys())]
    return presets


def get_presets_enum(export_format):
    presets = create_preset_enum(get_presets(export_format))
    return presets


mode_bundle_types = [
    ('NAME', 'Name', "Bundle by matching object names", 'SYNTAX_OFF', 0),
    ('PARENT', 'Parent', "Bundle by the parent object", 'FILE_PARENT', 1),
    ('COLLECTION', 'Collection', "Bundle by 'Collections'", 'GROUP', 2),
    ('SCENE', 'Scene', "Bundle by current scene", 'SCENE_DATA', 3)
]

mode_pivot_types = [
    ('OBJECT_FIRST', 'First Name', "Pivot at the first object sorted by name", 'FILE_TEXT', 1),
    ('OBJECT_LOWEST', 'Lowest Object', "Pivot at the lowest Z object's pivot", 'SORT_ASC', 2),
    ('BOUNDS_BOTTOM', 'Bottom Center', "Pivot at the bottom center of the bounds of the bundle", 'AXIS_TOP', 3),
    ('SCENE', 'Scene 0,0,0', "Pivot at the Scene center 0,0,0'", 'GRID', 4),
    ('PARENT', 'Parent', "Pivot from the parent object", 'FILE_PARENT', 5),
    ('EMPTY', 'Empty Gizmo', "Empty gizmo object of: Arrow, Plain Axes, Single Arrow>; global for all bundles (must be selected)", 'EMPTY_AXIS', 6),
    ('EMPTY_LOCAL', 'Empty Local Gizmo', "You need to have an empty of type Arrow, Plain Axes or Single Arrow located inside the bundle and its name needs to start with 'pivot'; for example 'pivot.001'", 'EMPTY_ARROWS', 7),
    ('COLLECTION', 'Collection', "Pivot from the collection instance offset parameter (Object Properties->Collection->X,Y,Z)", 'GROUP', 8)
]

ue4_collider_prefixes = {'UBX', 'UCP', 'USP', 'UCX'}

debug = False
