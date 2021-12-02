
import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty

from . import control_rig_data as ctrl_data
from . import control_rig_utils as ctrl_utils
from . import custom_slider_utils

from ..core import shape_key_utils
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils


class FACEIT_OT_SearchShapeKeys(bpy.types.Operator):
    ''' Invoke a search popup for all Shape Keys on registered objects'''
    bl_idname = 'faceit.search_shape_keys'
    bl_label = 'Search Popup'
    bl_property = 'shape'

    shape: EnumProperty(
        name='Target',
        items=custom_slider_utils.get_custom_sliders_from_faceit_objects_enum,
        description='The Shape that will be driven by the new controller',)

    def execute(self, context):
        self.report({'INFO'}, "You've selected: %s" % self.shape)
        context.scene.faceit_new_slider = self.shape
        for region in context.area.regions:
            region.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}


class FACEIT_OT_SetupCustomController(bpy.types.Operator):
    '''Setup Controllers for shapes that are not covered by the standart control rig.'''
    bl_idname = 'faceit.setup_custom_controller'
    bl_label = 'Custom Controller'
    bl_options = {'UNDO', 'INTERNAL'}

    new_slider: StringProperty(
        name='New Custom Slider',
        default='',
        options={'SKIP_SAVE', 'HIDDEN'},
    )
    region: EnumProperty(
        name='Region',
        items=ctrl_utils.get_face_region_items,
    )

    driver_exists: BoolProperty(
        name='The Shape Key is already driven',
        default=False,
        options={'SKIP_SAVE', 'HIDDEN'},
    )

    slider_range: EnumProperty(
        name='Range',
        items=(
            ('FULL', 'Full', 'Include negative range'),
            ('POS', 'Positive', 'Only positive Range'),
        )
    )

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                return ctrl_rig.faceit_crig_objects or context.scene.faceit_face_objects

    def invoke(self, context, event):

        for obj in futils.get_faceit_objects_list():
            if shape_key_utils.has_shape_keys(obj):
                if obj.data.shape_keys.animation_data:
                    dr = obj.data.shape_keys.animation_data.drivers.find(
                        'key_blocks["{}"].value'.format(self.new_slider))
                    if dr:
                        self.driver_exists = True
                        break

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        if self.driver_exists:
            row = layout.row()
            row.label(text='WARNING!')
            row = layout.row()
            row.label(text='Existing Drivers will be cleared!')

        row = layout.row(align=True)
        row.prop(context.scene, 'faceit_new_slider', text='')
        row.operator('faceit.search_shape_keys', text='Search Shape Keys', icon='VIEWZOOM')

        row = layout.row()
        row.prop(self, 'region')
        row = layout.row()
        row.prop(self, 'slider_range')

    def execute(self, context):

        scene = context.scene

        c_rig = futils.get_faceit_control_armature()

        if not c_rig:
            self.report({'ERROR'}, 'No Control Armature found.')
            return{'CANCELLED'}
        if not c_rig.faceit_crig_targets:
            self.report(
                {'ERROR'},
                'No Control Rig target shapes found. Please update the rig or populate the target shapes first.')
            return{'CANCELLED'}

        if context.active_object != c_rig:
            futils.set_active_object(c_rig.name)

        try:
            self.new_slider = scene.faceit_new_slider
        except:
            self.report({'WARNING'}, ' The shape doesn\'t exist on registered objects')
            return{'CANCELLED'}

        crig_targets = c_rig.faceit_crig_targets
        item = None
        if self.new_slider not in crig_targets:
            item = crig_targets.add()
            item.index = len(crig_targets) - 1
            item.name = self.new_slider
            item.amplify = 1.0
            item.region = self.region
            item.custom_slider = True
            target_item = item.target_shapes.add()
            target_item.name = self.new_slider

        custom_slider_utils.generate_extra_sliders(context, self.new_slider, 'full_range' if self.slider_range ==
                                                   'FULL' else 'pos_range', rig_obj=c_rig, overwrite=True)

        face_objects = futils.get_faceit_objects_list()
        connected_any = False
        for obj in face_objects:

            missing_shapes = []

            shapekeys = obj.data.shape_keys

            if not shapekeys:
                self.report({'WARNING'}, 'Object {} contains no Shape Keys'.format(obj.name))
                continue

            if not hasattr(shapekeys, 'key_blocks'):
                self.report({'WARNING'}, 'Object {} contains no Shape Keys'.format(obj.name))
                continue

            result, bone_name = ctrl_data.get_driver_from_retarget_dictionary_fixed_slider_range(
                self.new_slider, self.new_slider, c_rig, shapekeys, custom_slider=True, current_range='all'
                if self.slider_range == 'FULL' else 'pos')

            if bone_name and item:
                item.slider_name = bone_name

            if result == False:
                missing_shapes.append(self.new_slider)

            connected_any = True
        if connected_any:
            self.report({'INFO'}, 'Succesfully created Custom Controller {}'.format(self.new_slider))
        else:
            self.report({'WARNING'}, 'Wasn\'t able to connect any drivers for the new controller {}.'.format(self.new_slider))

        return{'FINISHED'}


class FACEIT_OT_RemoveCustomController(bpy.types.Operator):
    ''' Remove Custom Controllers from control rig and crig_targets '''
    bl_idname = 'faceit.remove_custom_controller'
    bl_label = 'Remove Custom Controller'
    bl_options = {'UNDO', 'INTERNAL'}

    custom_slider: EnumProperty(
        name='Target',
        items=custom_slider_utils.get_custom_sliders_in_crig_targets_enum,
        description='The Shape that will be driven by the new controller',)

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                if ctrl_rig.faceit_crig_objects or context.scene.faceit_face_objects:
                    if len(ctrl_rig.faceit_crig_targets) > 52:
                        return True

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        c_rig = futils.get_faceit_control_armature()
        if c_rig.faceit_crig_targets:
            if self.custom_slider:
                row = layout.row(align=True)
                row.prop(self, 'custom_slider', text='', icon='TRASH')
            else:
                row = layout.row(align=True)
                row.label(text='No Custom Controllers found.')
        else:
            row = layout.row(align=True)
            row.label(text='Update the Control Rig.')

    def execute(self, context):

        scene = context.scene

        c_rig = futils.get_faceit_control_armature()

        if not c_rig:
            self.report({'ERROR'}, 'No Control Armature found.')
            return{'CANCELLED'}

        if context.active_object != c_rig:
            futils.set_active_object(c_rig.name)

        crig_targets = c_rig.faceit_crig_targets
        found_index = crig_targets.find(self.custom_slider)
        if found_index != -1:

            # Remove Drivers!
            crig_objects = ctrl_utils.get_crig_objects_list(c_rig)

            for obj in crig_objects:

                shapekeys = obj.data.shape_keys

                if not shapekeys:
                    continue

                if not hasattr(shapekeys, 'key_blocks'):
                    # self.report({'WARNING'}, 'Object {} contains no Shape Keys'.format(obj.name))
                    continue

                dp = 'key_blocks["{}"].value'.format(self.custom_slider)

                shapekeys.driver_remove(dp, -1)

            # Remove Bones
            mode = context.mode
            # bpy.ops.object.mode_set(mode='POSE')
            remove_bones = custom_slider_utils.get_all_slider_bones(c_rig, filter=self.custom_slider)
            bpy.ops.object.mode_set(mode='EDIT')

            for bone_name in remove_bones:
                edit_bones = c_rig.data.edit_bones
                bone = edit_bones[bone_name]
                edit_bones.remove(bone)

            bpy.ops.object.mode_set(mode=mode)

            if c_rig.faceit_crig_targets_index >= found_index:
                c_rig.faceit_crig_targets_index -= 1

            crig_targets.remove(found_index)
        else:
            self.report({'ERROR'}, 'Custom Slider not found.')
            return{'CANCELLED'}

        return{'FINISHED'}
