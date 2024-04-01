
import os

from mathutils import Vector
from .control_rig_utils import get_crig_objects_list, load_control_rig_template, save_control_rig_template
import json
import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty, IntProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper


from ..core.retarget_list_utils import get_target_shapes_dict
from ..core import faceit_utils as futils
from ..core.faceit_data import get_face_region_items
from ..core.shape_key_utils import has_shape_keys
from . import custom_slider_utils
from .control_rig_data import get_driver_from_retarget_dictionary_fixed_slider_range, get_pose_bone_range_from_limit_constraint


class FACEIT_OT_SearchShapeKeys(bpy.types.Operator):
    ''' Invoke a search popup for all Shape Keys on registered objects'''
    bl_idname = 'faceit.search_shape_keys'
    bl_label = 'Search Popup'
    bl_property = 'shape'

    shape: EnumProperty(
        name='Target',
        items=custom_slider_utils.get_custom_sliders_enum_for_active_ctrl_rig,
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
        # update=update_slider,
        options={'SKIP_SAVE', 'HIDDEN'},
    )
    region: EnumProperty(
        name='Region',
        items=get_face_region_items,
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
            ('POS', 'Positive Only', 'Only positive Range'),
        )
    )

    @classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                return ctrl_rig.faceit_crig_objects or context.scene.faceit_face_objects

    def invoke(self, context, event):
        for obj in futils.get_faceit_objects_list():
            if has_shape_keys(obj):
                if obj.data.shape_keys.animation_data:
                    dr = obj.data.shape_keys.animation_data.drivers.find(
                        'key_blocks["{}"].value'.format(self.new_slider))
                    if dr:
                        self.driver_exists = True
                        break
        if not context.scene.faceit_new_slider:
            self.report({'ERROR'}, 'No custom shape keys were found on the registered objects.')
            return {'CANCELLED'}
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
        # Show the scene property in the UI
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
            return {'CANCELLED'}
        if not c_rig.faceit_crig_targets:
            self.report(
                {'ERROR'},
                'No Control Rig target shapes found. Please update the rig or populate the target shapes first.')
            return {'CANCELLED'}
        if context.active_object != c_rig:
            futils.set_active_object(c_rig.name)
        # Get the slider name from the scene property
        self.new_slider = scene.faceit_new_slider
        crig_targets = c_rig.faceit_crig_targets
        item = None
        if self.new_slider not in crig_targets:
            item = crig_targets.add()
            item.name = self.new_slider
            item.amplify = 1.0
            item.region = self.region
            item.custom_slider = True
            item.slider_range = self.slider_range
            target_item = item.target_shapes.add()
            target_item.name = self.new_slider
        item.slider_name = custom_slider_utils.generate_extra_sliders(
            context, self.new_slider, 'full_range' if self.slider_range == 'FULL' else 'pos_range', rig_obj=c_rig, overwrite=True)
        faceit_objects = futils.get_faceit_objects_list()
        connected_any = False
        for obj in faceit_objects:
            shapekeys = obj.data.shape_keys
            if not shapekeys:
                self.report({'WARNING'}, 'Object {} contains no Shape Keys'.format(obj.name))
                continue
            if not hasattr(shapekeys, 'key_blocks'):
                self.report({'WARNING'}, 'Object {} contains no Shape Keys'.format(obj.name))
                continue
            _result, _bone_name = get_driver_from_retarget_dictionary_fixed_slider_range(
                self.new_slider, self.new_slider, c_rig, shapekeys, custom_slider=True, current_range='all'
                if self.slider_range == 'FULL' else 'pos')
            connected_any = True
            # if bone_name and item:
            #     item.slider_name = bone_name

        if connected_any:
            self.report({'INFO'}, 'Succesfully created Custom Controller {}'.format(self.new_slider))
        else:
            self.report({'WARNING'}, 'Wasn\'t able to connect any drivers for the new controller {}.'.format(self.new_slider))
        try:
            bpy.ops.faceit.rearrange_custom_controllers()
        except RuntimeError:
            pass
        return {'FINISHED'}


class FACEIT_OT_SaveControlRigTemplate(bpy.types.Operator, ExportHelper):
    ''' Save Target Shapes and Controllers to a template file (.json) '''
    bl_idname = 'faceit.save_control_rig_template'
    bl_label = 'Save Control Rig Template'
    bl_options = {'UNDO', }

    filepath: StringProperty(
        subtype="FILE_PATH",
        default='json'
    )

    filter_glob: StringProperty(
        default='*.json;',
        options={'HIDDEN'},
    )
    save_regions: BoolProperty(
        name='Save Regions',
        description='Save the regions in this profile',
        default=True
    )
    save_amplify_values: BoolProperty(
        name='Save Amplify Values',
        description='Save the amplify values in this profile',
        default=True
    )
    filename_ext = '.json'

    @classmethod
    def poll(cls, context):
        c_rig = futils.get_faceit_control_armature()
        if c_rig:
            return c_rig.faceit_crig_targets

        # retarget_list = get_active_retarget_list()
        # if retarget_list:
        #     if any([item.target_shapes for item in retarget_list]):

    def invoke(self, context, event):
        self.filepath = 'capture_profile.json'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        c_rig = futils.get_faceit_control_armature()
        data = save_control_rig_template(c_rig, self.save_regions, self.save_amplify_values)
        if not data:
            self.report({'ERROR'}, 'Export Failed. Could not find retarget data')
            return {'CANCELLED'}

        if not self.filepath.endswith('.json'):
            self.filepath += '.json'

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        self.report({'INFO'}, 'Exported to {}'.format(self.filepath))

        return {'FINISHED'}


class FACEIT_OT_LoadControlRigTemplate(bpy.types.Operator, ImportHelper):
    ''' Load Target Shapes and Controllers from a template file (.json) '''
    bl_idname = 'faceit.load_control_rig_template'
    bl_label = 'Custom Controllers from Template'
    bl_options = {'UNDO', }

    filepath: StringProperty(
        subtype="FILE_PATH",
        default='capture_profile.json'
    )
    filter_glob: StringProperty(
        default='*.json;',
        options={'HIDDEN'},
    )
    load_amplify_values: BoolProperty(
        name='Load Amplify Values',
        description='Load the amplify values saved in this profile',
        default=True,
    )
    load_regions: BoolProperty(
        name='Load Regions',
        description='Load the regions saved in this profile',
        default=True,
    )
    overwrite_existing_controllers: BoolProperty(
        name='Overwrite Existing Controllers',
        description='Overwrite existing controllers with the same name. If this is True the controllers will be overwritten, if False the controllers will be skipped',
        default=False,)

    @classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                return ctrl_rig.faceit_crig_objects or context.scene.faceit_face_objects

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='Import Settings')
        # row = layout.row()
        # row.prop(self, 'load_amplify_values')
        # row = layout.row()
        # row.prop(self, 'load_regions')
        row = layout.row()
        row.prop(self, 'overwrite_existing_controllers')

    def execute(self, context):
        c_rig = futils.get_faceit_control_armature()
        if not c_rig:
            self.report({'ERROR'}, 'No Control Armature found.')
            return {'CANCELLED'}
        if not c_rig.faceit_crig_targets:
            self.report(
                {'ERROR'},
                'No Control Rig target shapes found. Please update the rig or populate the target shapes first.')
            return {'CANCELLED'}
        if context.active_object != c_rig:
            futils.set_active_object(c_rig.name)
        _filename, extension = os.path.splitext(self.filepath)
        if extension != '.json':
            self.report({'ERROR'}, 'You need to provide a file of type .json')
            return {'CANCELLED'}
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, f"The specified filepath does not exist: {os.path.realpath(self.filepath)}")
            return {'CANCELLED'}
        created_any_custom_controllers = False
        with open(self.filepath, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                created_any_custom_controllers = load_control_rig_template(
                    context,
                    c_rig,
                    data,
                    overwrite_existing_controllers=self.overwrite_existing_controllers,
                )
        if created_any_custom_controllers:
            # Reconnect the drivers.
            bpy.ops.faceit.setup_control_drivers('EXEC_DEFAULT')
            self.report({'INFO'}, 'Imported template from {}'.format(self.filepath))
        else:
            self.report({'INFO'}, 'No custom controllers were created. Please check the console for more info.')
        return {'FINISHED'}


class FACEIT_OT_RemoveCustomController(bpy.types.Operator):
    ''' Remove Custom Controllers from control rig and crig_targets '''
    bl_idname = 'faceit.remove_custom_controller'
    bl_label = 'Remove Custom Controller'
    bl_options = {'UNDO', 'INTERNAL'}
    bl_property = 'custom_slider'

    custom_only: BoolProperty(
        name='Custom Only',
        description='Only remove custom controllers',
        default=True,
    )
    custom_slider: EnumProperty(
        name='Target',
        items=custom_slider_utils.get_custom_sliders_in_crig_targets_enum,
        description='The Shape that will be driven by the new controller',)

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
            return True
            # return (ctrl_rig.faceit_crig_targets[ctrl_rig.faceit_crig_targets_index] in custom_slider_utils.get_slider_shape_names_in_crig(c_rig))

    def invoke(self, context, event):

        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):
        c_rig = futils.get_faceit_control_armature()
        if not c_rig:
            self.report({'ERROR'}, 'No Control Armature found.')
            return {'CANCELLED'}
        if context.active_object != c_rig:
            futils.set_active_object(c_rig.name)
        crig_targets = c_rig.faceit_crig_targets
        found_index = crig_targets.find(self.custom_slider)
        if found_index != -1:
            # Remove Drivers!
            crig_objects = get_crig_objects_list(c_rig)
            for obj in crig_objects:
                shapekeys = obj.data.shape_keys
                if not shapekeys:
                    continue
                if not hasattr(shapekeys, 'key_blocks'):
                    continue
                dp = 'key_blocks["{}"].value'.format(self.custom_slider)
                shapekeys.driver_remove(dp, -1)
                sk = shapekeys.key_blocks.get(self.custom_slider)
                if sk:
                    sk.value = 0
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
            try:
                bpy.ops.faceit.rearrange_custom_controllers()
            except RuntimeError:
                pass
        else:
            self.report({'ERROR'}, 'Custom Slider not found.')
            return {'CANCELLED'}
        return {'FINISHED'}


class FACEIT_OT_RearrangeCustomControllers(bpy.types.Operator):
    ''' Rearrange Custom Controllers in crig_targets '''
    bl_idname = 'faceit.rearrange_custom_controllers'
    bl_label = 'Rearrange Custom Controllers'
    bl_options = {'UNDO', 'INTERNAL'}

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                return True

    def execute(self, context):
        c_rig = futils.get_faceit_control_armature()
        if not c_rig:
            self.report({'ERROR'}, 'No Control Armature found.')
            return {'CANCELLED'}
        max_rows = c_rig.faceit_crig_rows
        if context.active_object != c_rig:
            futils.set_active_object(c_rig.name)
        custom_slider_utils.get_properties_for_sliders(c_rig)
        slider_shape_names = custom_slider_utils.get_slider_shape_names_in_crig(c_rig, custom_only=False)
        # slider_shape_names.insert(0, 'forceMouthClose')
        # slider_bone_names = [() in slider_shape_names]
        bpy.ops.object.mode_set(mode='EDIT')
        ref_slider_parent_bone = c_rig.data.edit_bones.get('c_slider_ref_parent')
        init_pos = ref_slider_parent_bone.head.copy()
        ref_length = ref_slider_parent_bone.length
        for i, shape_name in enumerate(slider_shape_names):
            slider_txt = c_rig.data.edit_bones[f'c_{shape_name}_slider_txt']
            slider_parent = c_rig.data.edit_bones[f'c_{shape_name}_slider_parent']
            slider = c_rig.data.edit_bones[f'c_{shape_name}_slider']
            pos = init_pos.copy()
            slider_pos_x = i // max_rows * ref_length * 2
            slider_pos_z = i % max_rows * ref_length / 2
            pos = Vector((
                pos.x + slider_pos_x,
                pos.y,
                init_pos.z + slider_pos_z)
            )
            vec = pos - slider.head
            for bone in (slider_parent, slider, slider_txt):
                bone.translate(vec)
        bpy.ops.object.mode_set(mode='POSE')
        return {'FINISHED'}


class FACEIT_OT_MoveTargetShapeItem(bpy.types.Operator):
    '''Move a specific Expression Item index in the list. Also effects the expression actions '''
    bl_idname = "faceit.move_target_shape_item"
    bl_label = "Move"
    bl_options = {'UNDO', 'INTERNAL'}

    # the name of the facial part
    direction: bpy.props.EnumProperty(
        items=(
            ('UP', 'Up', ''),
            ('DOWN', 'Down', ''),
        ),
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        c_rig = futils.get_faceit_control_armature()
        idx = c_rig.faceit_crig_targets_index
        target_shapes = c_rig.faceit_crig_targets
        return target_shapes and idx >= 0 and idx < len(target_shapes)

    def execute(self, context):
        c_rig = futils.get_faceit_control_armature()
        index = c_rig.faceit_crig_targets_index
        target_shapes = c_rig.faceit_crig_targets

        add_index = -1 if self.direction == 'UP' else 1
        new_index = index + add_index

        if new_index == len(target_shapes) or new_index == -1:
            return {'CANCELLED'}
            # self.report({'ERROR'},)

        target_shapes.move(new_index, index)
        list_length = len(target_shapes) - 1
        new_index = index + (-1 if self.direction == 'UP' else 1)
        c_rig.faceit_crig_targets_index = max(0, min(new_index, list_length))
        try:
            bpy.ops.faceit.rearrange_custom_controllers()
        except RuntimeError:
            print('Wasn\'t able to rearrange the custom controllers.')
            pass
        return {'FINISHED'}
