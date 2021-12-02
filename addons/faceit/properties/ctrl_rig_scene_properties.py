
import bpy

from bpy.types import Object, PropertyGroup, Scene
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty


from ..core import faceit_data
from ..ctrl_rig.custom_slider_utils import get_custom_sliders_from_faceit_objects_enum


def is_armature_object(self, obj):
    if obj.library:
        return False
    if obj.type == 'ARMATURE' and obj.name in bpy.context.scene.objects:
        if 'FaceitControlRig' in obj.name or 'ctrl_rig_id' in obj:
            return True


# def update_cntrl_rig(self, object):

#     scene = bpy.context.scene
#     ctrl_rig = futils.get_faceit_control_armature()
#     if ctrl_rig == None:
#         print('control rig is None')
#         return
#     if scene.faceit_sync_cntrl_rig_settings:
#         try:
#             bpy.ops.faceit.load_faceit_settings_from_crig('INVOKE_DEFAULT', auto_sync=True)
#         except RuntimeError as ex:
#             error_report = "\n".join(ex.args)
#             print("Caught error:", error_report)


class FaceRegions(PropertyGroup):
    eyes: BoolProperty(
        name='Eyes',
        options=set(),
        default=True,
    )
    brows: BoolProperty(
        name='Brows',
        options=set(),
        default=True,
    )
    cheeks: BoolProperty(
        name='Cheeks',
        options=set(),
        default=True,
    )
    nose: BoolProperty(
        name='Nose',
        options=set(),
        default=True,
    )
    mouth: BoolProperty(
        name='Mouth',
        options=set(),
        default=True,
    )
    tongue: BoolProperty(
        name='Tongue',
        options=set(),
        default=True,
    )
    other: BoolProperty(
        name='Other',
        options=set(),
        default=True,
    )

    def get_active_regions(self):
        active_regions = {
            'eyes': self.eyes,
            'brows': self.brows,
            'cheeks': self.cheeks,
            'nose': self.nose,
            'mouth': self.mouth,
            'tongue': self.tongue,
            'other': self.other,
        }
        return active_regions


def get_face_region_items(self, context):
    region_items = []
    for r in faceit_data.FACE_REGIONS_BASE.keys():
        region_items.append((r, r, r))
    return region_items


# class Shape_Drivers(PropertyGroup):
#     transform_type: StringProperty(
#         name='transform_type',
#         default='LOC_Y'
#     )
#     transform_space: StringProperty(
#         name='transform_space',
#         default='LOCAL_SPACE',
#     )
#     expression: StringProperty(
#         name='expression',
#         default='',
#     )
#     range: StringProperty(
#         name='range',
#         default='all',
#     )
#     main_dir: IntProperty(
#         name='range',
#         default=1,
#     )

class Target_Objects(PropertyGroup):
    name: StringProperty(
        name='Object Name',
        description='object name'
    )
    # Problem with object ids, they have to be deleted globally,
    # otherwise they will never be none. Even if deleted from scene..
    obj_pointer: PointerProperty(
        name='Object',
        type=Object
    )


class TargetShapes(PropertyGroup):
    name: StringProperty(
        name='Target Shape',
        description='The Target Shape',
        default='---',
    )


class ControlRigShapes(PropertyGroup):

    name: StringProperty(
        name='Expression Name',
        description='The Expression Name',
        options=set(),
    )
    custom_slider: BoolProperty(
        name='Custom Slider',
        default=False,
        description='Whether this is a custom slider or standart ARKit target',
    )
    if bpy.app.version >= (2, 90, 0):
        amplify: FloatProperty(
            name='Amplify Value',
            default=1.0,
            description='Use the Amplify Value to multiply all animation values by a factor. Increase Shape Key ranges to aninate beyond the range [0,1]',
            soft_min=0.0,
            soft_max=10.0,
            override={'LIBRARY_OVERRIDABLE'},
        )
    else:
        amplify: FloatProperty(
            name='Amplify Value',
            default=1.0,
            description='Use the Amplify Value to multiply all animation values by a factor. Increase Shape Key ranges to aninate beyond the range [0,1]',
            soft_min=0.0,
            soft_max=10.0,
        )
    target_list_index: IntProperty(
        name='Target Shape Index',
        default=0,
        description='Index of Active Target Shape',
        options=set(),
    )
    target_shapes: CollectionProperty(
        name='Target Shapes',
        type=TargetShapes,
        description='Target Shapes for this ARKit shape. Multiple target shapes possible',
        options=set(),
    )
    slider_name: StringProperty(
        name='Bone Name',
        description='The name of the slider controlling this shape',
        default='',
    )

    region: EnumProperty(
        name='Face Regions',
        items=get_face_region_items,
        options=set(),
    )


def register():

    Scene.faceit_draw_handler_name = StringProperty(
        name='draw handler',
        default=''
    )

    Scene.faceit_control_armature = PointerProperty(
        name='The Control Rig',
        description='the control rig used to control and manipulate the Faceit Expressions. Create override to load linked control rigs.',
        type=Object, poll=is_armature_object)

    Scene.faceit_face_regions = PointerProperty(
        name='Face Regions',
        type=FaceRegions,
    )

    Scene.faceit_show_crig_regions = BoolProperty(
        name='Show Regions',
        default=False,
        description='Change Regions of all Target Shapes.'
    )
    Scene.faceit_show_crig_target_shapes = BoolProperty(
        name='Show Target Shapes',
        default=False,
        description='View and Edit Target Shapes.'
    )
    Scene.faceit_crig_targets = CollectionProperty(
        name='Control Rig Target Expressions',
        type=ControlRigShapes,
    )
    Scene.faceit_crig_targets_index = IntProperty(
        name='CRig Shapes Index',
        default=0,
        options=set(),
    )

    Scene.faceit_new_slider = EnumProperty(
        name='Target',
        items=get_custom_sliders_from_faceit_objects_enum,
        description='The Shape that will be driven by the new controller',
    )
    if bpy.app.version >= (2, 90, 0):
        Object.faceit_crig_targets_index = IntProperty(
            name='CRig Shapes Index',
            default=0,
            options=set(),
            override={'LIBRARY_OVERRIDABLE'},
        )

        Object.faceit_crig_targets = CollectionProperty(
            name='Control Rig Target Expressions',
            type=ControlRigShapes,
            override={'LIBRARY_OVERRIDABLE'},
        )

        Object.faceit_crig_objects = CollectionProperty(
            name='Objects Driven',
            type=Target_Objects,
        )

        Object.faceit_crig_objects_index = IntProperty(
            name='CRig Objects Index',
            default=0,
            options=set(),
            override={'LIBRARY_OVERRIDABLE'},
        )
    else:
        Object.faceit_crig_targets_index = IntProperty(
            name='CRig Shapes Index',
            default=0,
            options=set(),
        )

        Object.faceit_crig_targets = CollectionProperty(
            name='Control Rig Target Expressions',
            type=ControlRigShapes,
        )

        Object.faceit_crig_objects = CollectionProperty(
            name='Objects Driven',
            type=Target_Objects,
        )

        Object.faceit_crig_objects_index = IntProperty(
            name='CRig Objects Index',
            default=0,
            options=set(),
        )


def unregister():

    del Scene.faceit_draw_handler_name
    del Scene.faceit_control_armature
    del Scene.faceit_face_regions
    del Scene.faceit_show_crig_regions

    del Scene.faceit_crig_targets
    del Scene.faceit_crig_targets_index
    # del Scene.faceit_sync_cntrl_rig_settings
    del Scene.faceit_new_slider

    del Object.faceit_crig_targets
    del Object.faceit_crig_objects_index
    del Object.faceit_crig_objects
