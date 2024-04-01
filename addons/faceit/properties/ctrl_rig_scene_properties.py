
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, IntProperty, PointerProperty,
                       StringProperty)
from bpy.types import Object, PropertyGroup, Scene

from ..core.retarget_list_base import FaceRegionsBase, RetargetShapesBase
from ..ctrl_rig.custom_slider_utils import get_custom_sliders_enum_for_active_ctrl_rig, get_slider_from_shape
from ..ctrl_rig.control_rig_utils import get_crig_objects_list, get_slider_bone_name_from_arkit_driver_dict
from ..core.shape_key_utils import set_slider_max
from ..core.retarget_list_utils import get_index_of_collection_item, get_target_shape_keys


def is_armature_object(self, obj):
    if obj.library:
        return False
    if obj.type == 'ARMATURE' and obj.name in bpy.context.scene.objects:
        if 'FaceitControlRig' in obj.name or 'ctrl_rig_id' in obj:
            return True


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


def update_amplify_id_property(expression_name, amplify_value, ctrl_rig):
    '''Updates the amplify value for the specific expression on the rig object
        This is important because the control rig otherwise can't be used without the faceit add-on.
        Examples: animators / renderfarms / ...
    '''
    ctrl_rig[expression_name] = amplify_value


def update_shape_key_ranges_based_on_amplify(target_shape_item, ctrl_rig):
    '''Update the shape key ranges based on the amplify value'''
    target_sk = get_target_shape_keys(target_shape_item, objects=get_crig_objects_list(ctrl_rig))
    for sk in target_sk:
        set_slider_max(sk, value=target_shape_item.amplify)
        sk.value = target_shape_item.amplify


def update_ctrl_rig_amplify_value(self, context):
    '''Update function for the amplify values on the control rig.'''
    # get the control rig that holds the data.
    ctrl_rig = self.id_data
    # set the active index
    idx = get_index_of_collection_item(self)
    setattr(ctrl_rig, "faceit_crig_targets_index", idx)
    # update the shape key ranges
    if bpy.context.preferences.addons["faceit"].preferences.dynamic_shape_key_ranges:
        update_shape_key_ranges_based_on_amplify(self, ctrl_rig)
    # Store the value for drivers.
    update_amplify_id_property(self.name, self.amplify, ctrl_rig)


class ControlRigShapes(RetargetShapesBase, PropertyGroup):

    custom_slider: BoolProperty(
        name='Custom Slider',
        default=False,
        description='Whether this is a custom slider or standart ARKit target',
    )
    slider_range: EnumProperty(
        name='Slider Range',
        items=(
            ('FULL', 'Full', 'Full Range'),
            ('POS', 'Positive', 'Positive Range'),
            ('NONE', 'None', 'No Range set')
        ),
        default='NONE',
    )
    slider_name: StringProperty(
        name='Bone Name',
        description='The name of the slider controlling this shape',
        default='',
    )
    if bpy.app.version >= (2, 90, 0):
        amplify: FloatProperty(
            name='Amplify Value',
            default=1.0,
            description='Use the Amplify Value to multiply all animation values by a factor. Increase Shape Key ranges to aninate beyond the range [0,1]',
            soft_min=0.0,
            soft_max=3.0,
            min=-1.0,
            max=10.0,
            override={'LIBRARY_OVERRIDABLE'},
            update=update_ctrl_rig_amplify_value
        )
    else:
        amplify: FloatProperty(
            name='Amplify Value',
            default=1.0,
            description='Use the Amplify Value to multiply all animation values by a factor. Increase Shape Key ranges to aninate beyond the range [0,1]',
            soft_min=0.0,
            soft_max=3.0,
            min=-1.0,
            max=10.0,
            update=update_ctrl_rig_amplify_value
        )

    def get_slider_bone(self):
        # Get the bone that controls this shape
        pass


def update_slider_rows(self, context):
    if context.mode in ('OBJECT', 'POSE'):
        bpy.ops.faceit.rearrange_custom_controllers('EXEC_DEFAULT')


def update_crig_target_index(self, context):
    c_rig = context.scene.faceit_control_armature
    active_target = c_rig.faceit_crig_targets[c_rig.faceit_crig_targets_index]
    if not c_rig.mode == 'POSE':
        return
    slider_name = active_target.slider_name
    slider = None
    if not slider_name:
        if active_target.custom_slider:
            slider = get_slider_from_shape(c_rig, active_target.name, custom_only=False)
        else:
            slider_name = get_slider_bone_name_from_arkit_driver_dict(c_rig, active_target.name)
    if not slider:
        slider = c_rig.pose.bones.get(slider_name)
    if slider:
        for b in c_rig.data.bones:
            b.select = False
        c_rig.data.bones.active = slider.bone
        slider.bone.select = True
    # try:
    #     bpy.ops.faceit.select_bone_from_source_shape('EXEC_DEFAULT', expression=active_target.name)
    # except RuntimeError:
    #     pass


def register():

    Scene.faceit_draw_handler_name = StringProperty(
        name='draw handler',
        default=''
    )
    Scene.faceit_show_landmarks_ctrl_rig = BoolProperty(
        name="Show Landmarks Panel",
        description="Show the Landmarks Panel in the Control Rig Tab",
        default=False,
    )
    Scene.faceit_control_armature = PointerProperty(
        name='The Control Rig',
        description='the control rig used to control and manipulate the Faceit Expressions. Create override to load linked control rigs.',
        type=Object, poll=is_armature_object)

    Scene.faceit_crig_targets = CollectionProperty(
        name='Control Rig Target Expressions',
        type=ControlRigShapes,
    )
    Scene.faceit_crig_targets_index = IntProperty(
        name='CRig Shapes Index',
        default=0,
        options=set(),
        update=update_crig_target_index,
    )
    # Scene.faceit_crig_force_mouth_close_slider_position_index = IntProperty(
    #     name='Force Mouth Close Slider Index',
    #     default=0,
    #     min=0,
    # )
    Scene.faceit_new_slider = EnumProperty(
        name='Target',
        items=get_custom_sliders_enum_for_active_ctrl_rig,
        description='The Shape that will be driven by the new controller',
    )
    if bpy.app.version >= (2, 90, 0):
        Object.faceit_crig_targets_index = IntProperty(
            name='CRig Shapes Index',
            default=0,
            options=set(),
            override={'LIBRARY_OVERRIDABLE'},
            update=update_crig_target_index,
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

        Object.faceit_crig_face_regions = PointerProperty(
            name='Face Regions (Control Rig)',
            type=FaceRegionsBase,
            override={'LIBRARY_OVERRIDABLE'},
        )
        Object.faceit_crig_rows = IntProperty(
            name='Custom Slider Rows',
            default=10,
            min=1,
            max=1000,
            description='The number of rows for the custom slider panel in the Control Rig',
            update=update_slider_rows,
            override={'LIBRARY_OVERRIDABLE'},
        )
    else:
        Object.faceit_crig_targets_index = IntProperty(
            name='CRig Shapes Index',
            default=0,
            options=set(),
            update=update_crig_target_index,
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
        Object.faceit_crig_face_regions = PointerProperty(
            name='Face Regions (Control Rig)',
            type=FaceRegionsBase,
        )
        Object.faceit_crig_rows = IntProperty(
            name='Custom Slider Rows',
            default=10,
            min=1,
            max=1000,
            description='The number of rows for the custom slider panel in the Control Rig',
            update=update_slider_rows,
            options=set(),
        )


def unregister():

    del Scene.faceit_draw_handler_name
    del Scene.faceit_control_armature

    del Scene.faceit_crig_targets
    del Scene.faceit_crig_targets_index
    del Scene.faceit_new_slider

    del Object.faceit_crig_targets
    del Object.faceit_crig_objects_index
    del Object.faceit_crig_objects
    del Object.faceit_crig_face_regions
