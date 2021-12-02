
import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty, FloatProperty

from ..core import fc_dr_utils
from ..core import faceit_utils as futils
from ..retargeting import detection_manager
from ..core import shape_key_utils as sk_utils
from ..retargeting import retarget_list_utils as rutils
from ..ctrl_rig.control_rig_animation_operators import CRIG_ACTION_SUFFIX
from ..ctrl_rig import control_rig_utils as ctrl_utils


class FACEIT_OT_InitFBXRetargeting(bpy.types.Operator):
    '''Initialize the retargeting list and try to match shapes automatically'''
    bl_idname = 'faceit.init_fbx_retargeting'
    bl_label = 'Initialize Retargeting'
    bl_options = {'UNDO', 'INTERNAL'}

    levenshtein_ratio: FloatProperty(
        name='Similarity Ratio',
        default=1.0,
        description='The ratio can be used for fuzzy name comparison. Default: 1.0'
    )

    empty: BoolProperty(
        name='Empty',
        default=False,
        description='Register with Empty Targets',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    remove_prefix_source: StringProperty(
        name='Remove Prefix (Source)',
        description='Specify a Prefix that will be ignore during matching.'
    )
    remove_suffix_source: StringProperty(
        name='Remove Suffix (Source)',
        description='Specify a Suffix that will be ignore during matching.'
    )
    remove_prefix_target: StringProperty(
        name='Remove Prefix (Target)',
        description='Specify a Prefix that will be ignore during matching.'
    )
    remove_suffix_target: StringProperty(
        name='Remove Suffix (Target)',
        description='Specify a Suffix that will be ignore during matching.'
    )

    @classmethod
    def poll(self, context):

        retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping

        mapping_source = retarget_fbx_props.mapping_source

        if mapping_source == 'OBJECT':
            source = retarget_fbx_props.source_obj
        else:
            source = retarget_fbx_props.source_action

        target = retarget_fbx_props.target_obj != None or retarget_fbx_props.mapping_target != 'TARGET'

        return source and target

    def invoke(self, context, event):
        if self.empty == False:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):

        scene = context.scene

        retarget_fbx_props = scene.faceit_retarget_fbx_mapping
        retarget_list = retarget_fbx_props.mapping_list

        # | ------------------- MAPPING SOURCE ------------------------
        # | - Either a specific Object or a Shape Key Action (Shape Key Names)
        # | -----------------------------------------------------------
        mapping_source = retarget_fbx_props.mapping_source

        shape_key_names_source = []

        if self.empty:
            retarget_list.clear()
            return{'FINISHED'}

        if mapping_source == 'OBJECT':
            source_obj = retarget_fbx_props.source_obj
            if not source_obj:
                self.report({'ERROR'}, 'The Source Object is not valid')
                return{'CANCELLED'}

            if not sk_utils.has_shape_keys(source_obj):
                self.report({'ERROR'}, 'The Source Object has no Shape Keys')
                return{'CANCELLED'}

            shape_key_names_source = sk_utils.get_shape_key_names_from_objects([source_obj])

        elif mapping_source == 'ACTION':
            source_action = retarget_fbx_props.source_action
            if not source_action:
                self.report(
                    {'ERROR'},
                    'No registered objects found. Register Objects in Setup Panel or use single target object')
                return{'CANCELLED'}

            shape_key_names_source = sk_utils.get_shape_key_names_from_action(source_action)

        if not shape_key_names_source:
            self.report({'ERROR'}, 'No Shape Keys found in Source.')
            return{'CANCELLED'}

        # | ------------------- MAPPING TARGET ------------------------
        # | - Either a specific Object or all registered Objects (Shape Key Names)
        # | -----------------------------------------------------------
        mapping_target = retarget_fbx_props.mapping_target

        target_objects = []
        shape_key_names_target = []

        if mapping_target == 'TARGET':
            target_obj = retarget_fbx_props.target_obj
            if not target_obj:
                self.report({'ERROR'}, 'The Target Object is not valid')
                return{'CANCELLED'}
            if not sk_utils.has_shape_keys(target_obj):
                self.report({'ERROR'}, 'The Target Object has no Shape Keys')
                return{'CANCELLED'}

            target_objects = [target_obj, ]
            # shape_key_names_target = sk_utils.get_shape_key_names_from_objects([target_obj])

        elif mapping_target == 'FACEIT':
            target_objects = futils.get_faceit_objects_list()
            if not target_objects:
                self.report(
                    {'ERROR'},
                    'No registered objects found. Register Objects in Setup Panel or use single target object')
                return{'CANCELLED'}

        elif mapping_target == 'CRIG':
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                target_objects = ctrl_utils.get_crig_objects_list(c_rig)
            if not target_objects:
                self.report(
                    {'ERROR'},
                    'No registered objects found. Register Objects in Setup Panel or use single target object')
                return{'CANCELLED'}

        shape_key_names_target = sk_utils.get_shape_key_names_from_objects(target_objects)

        if not shape_key_names_target:
            self.report({'ERROR'}, 'the registered objects have no shape keys.')
            return{'CANCELLED'}

        match_names = {}
        new_names = []
        if self.remove_prefix_target or self.remove_suffix_target:
            new_names = []
            for name in shape_key_names_target:
                name_match = name
                if self.remove_prefix_target:
                    if name.startswith(self.remove_prefix_target):
                        name_match = name[len(self.remove_prefix_target):]
                if self.remove_suffix_target:
                    if name.endswith(self.remove_suffix_target):
                        name_match = name[:-len(self.remove_suffix_target)]
                new_names.append(name_match)
                match_names[name_match] = name

        retarget_list.clear()
        missing_shapes = []

        for i, source_shape in enumerate(shape_key_names_source):

            item = retarget_list.add()

            item.name = item.display_name = source_shape

            item.index = i

            if self.empty:
                continue

            if self.remove_prefix_source:
                if source_shape.startswith(self.remove_prefix_source):
                    source_shape = source_shape[len(self.remove_prefix_source):]
            if self.remove_suffix_source:
                if source_shape.endswith(self.remove_suffix_source):
                    source_shape = source_shape[:-len(self.remove_suffix_source)]
            if new_names:
                found_shape = detection_manager.detect_shape(
                    new_names,
                    source_shape,
                    min_levenshtein_ratio=self.levenshtein_ratio,
                    remove_suffix=self.remove_suffix_target,
                )
                found_shape = match_names.get(found_shape)
            else:
                found_shape = detection_manager.detect_shape(
                    shape_key_names_target,
                    source_shape,
                    min_levenshtein_ratio=self.levenshtein_ratio,
                    remove_prefix=self.remove_prefix_target,
                    remove_suffix=self.remove_suffix_target,
                )
            if found_shape:

                target_shape_count = len(item.target_shapes)
                target_item = item.target_shapes.add()
                target_item.index = target_shape_count
                target_item.parent_idx = i
                target_item.name = found_shape
                shape_key_names_target.remove(found_shape)
                continue

            missing_shapes.append(source_shape)

        if missing_shapes:
            for shape in reversed(missing_shapes):
                self.report({'WARNING'}, 'Couldn\'t find target shape for ARKit expression {}'.format(shape))

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


def get_enum_sk_actions(self, context):
    global actions
    actions = []
    for a in bpy.data.actions:
        if any(['key_block' in fc.data_path for fc in a.fcurves]):
            actions.append((a.name,)*3)

    # if not actions:
    #     actions.append(('-',)*3)

    return actions


def update_action_name(self, context):
    self.new_name = self.retarget_action + self.suffix


class FACEIT_OT_RetargetFBXAction(bpy.types.Operator):
    '''Retarget the Source Action to the populated target Shapes '''
    bl_idname = 'faceit.retarget_fbx_action'
    bl_label = 'Initialize Retargeting'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    retarget_action: EnumProperty(
        name='Source Action',
        items=get_enum_sk_actions,
        description='the Shape Key Action to Retarget',
        update=update_action_name,
    )

    suffix: StringProperty(
        name='Add Suffix',
        default='_retargeted',
        update=update_action_name,
    )

    new_name: StringProperty(
        name='New Action Name',
        description='Specify Name of the New Action'
    )

    populate_faceit: BoolProperty(
        name='Populate to all Faceit Objects',
        description='Activate the retargeted Action on all Faceit Objects.',
        default=True,
    )

    keep_undetected_shapes: BoolProperty(
        name='Keep undetected Fcurves',
        default=False,
    )

    bake_to_control_rig: BoolProperty(
        name='Bake to Control Rig',
        default=False,
        description='Loads the mocap action directly on the control rig. Creates a temp Action with the 52 Shape Keys.',
        options={'SKIP_SAVE', }
    )
    show_advanced_settings: BoolProperty(
        name='Show Advanced Settings',
        default=False,
        description='Blend in the advanced settings for this operator'
    )

    @classmethod
    def poll(self, context):

        retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping

        return retarget_fbx_props.mapping_list

    def invoke(self, context, event):

        retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping
        source_action = None
        if retarget_fbx_props.mapping_source == 'OBJECT':
            source_obj = retarget_fbx_props.source_obj
            if sk_utils.has_shape_keys(source_obj):
                if source_obj.data.shape_keys.animation_data:
                    source_action = source_obj.data.shape_keys.animation_data.action
        else:
            source_action = retarget_fbx_props.source_action

        if any(['key_block' in fc.data_path for fc in source_action.fcurves]):
            self.new_name = source_action.name+'_retargeted'
            self.retarget_action = source_action.name

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, 'retarget_action', icon='ACTION')
        # row = layout.row()
        # row.prop(self, 'suffix')

        row = layout.row()
        row.prop(self, 'new_name', icon='ACTION')

        if futils.get_faceit_control_armature():
            row = layout.row()
            row.prop(self, 'bake_to_control_rig', icon='CON_ARMATURE')
        if self.bake_to_control_rig:
            row = layout.row()
            row.label(text='Only works for ARKit recordings.')
        else:
            # row = layout.row()
            row = layout.row(align=True)
            row.prop(self, 'show_advanced_settings', icon='COLLAPSEMENU')
            if self.show_advanced_settings:
                row = layout.row()
                row.prop(self, 'keep_undetected_shapes', icon='ACTION')

    def execute(self, context):

        scene = context.scene

        retarget_fbx_props = scene.faceit_retarget_fbx_mapping
        retarget_list = retarget_fbx_props.mapping_list

        source_action = None

        source_action = bpy.data.actions.get(self.retarget_action)

        if not source_action:
            self.report(
                {'ERROR'},
                'No source Action found. choose a valid Shape Keys Action! ')
            return{'CANCELLED'}

        if self.bake_to_control_rig:
            c_rig = futils.get_faceit_control_armature()
            if not c_rig:
                self.report(
                    {'ERROR'},
                    'Can\'t find the active control rig. Please create/choose control rig first or import directly to the meshes.')
                return{'CANCELLED'}

            a_remove = bpy.data.actions.get('mocap_import')
            if a_remove:
                bpy.data.actions.remove(a_remove)

            target_action = source_action.copy()
            target_action.name = 'mocap_import'
            # target_action = bpy.data.actions.new('mocap_import')
        else:
            target_action = bpy.data.actions.get(self.new_name)
            if target_action:
                bpy.data.actions.remove(target_action)
            target_action = source_action.copy()
            target_action.name = self.new_name

        all_fcurve_data_paths = [fc.data_path for fc in source_action.fcurves]

        retargeted_any = False
        for item in retarget_list:

            if item.use_animation == False:
                continue

            target_shapes = item.target_shapes

            target_shapes_list = [t.name for t in target_shapes]

            source_shape = item.name
            data_paths = [
                'key_blocks["{}"].value'.format(source_shape),
                'key_blocks["{}"].slider_min'.format(source_shape),
                'key_blocks["{}"].slider_max'.format(source_shape)
            ]

            for dp in data_paths:
                fc = target_action.fcurves.find(dp)
                if fc:
                    source_is_target_shape = False
                    for target_shape in target_shapes_list:
                        fc_data_copy = fc_dr_utils.copy_fcurve_data(fc)
                        new_dp = dp.replace(source_shape, target_shape)
                        # Check if Source and Target Shape have the same data path
                        if not source_is_target_shape:
                            source_is_target_shape = bool(dp != new_dp)
                        fc_dr_utils.populate_stored_fcurve_data(
                            fc_data_copy, dp=new_dp, action=target_action, join_with_existing_data=False)
                        retargeted_any = True

                    if source_is_target_shape:
                        target_action.fcurves.remove(fc)

                    all_fcurve_data_paths.remove(dp)

        if all_fcurve_data_paths:
            for dp in all_fcurve_data_paths:
                self.report({'WARNING'}, 'Did not retarget fcurve with data_path {} '.format(dp))
                if not self.keep_undetected_shapes:
                    fc = target_action.fcurves.find(dp)
                    if fc:
                        target_action.fcurves.remove(fc)

        if retargeted_any:
            mapping_target = retarget_fbx_props.mapping_target
            target_objects = []
            if mapping_target == 'FACEIT':
                target_objects = futils.get_faceit_objects_list()
            elif mapping_target == 'CRIG':
                c_rig = futils.get_faceit_control_armature()
                if c_rig:
                    target_objects = ctrl_utils.get_crig_objects_list(c_rig)
            elif mapping_target == 'TARGET':
                target_objects = [retarget_fbx_props.target_obj, ]

            for ob in target_objects:
                if sk_utils.has_shape_keys(ob):
                    if not ob.data.shape_keys.animation_data:
                        ob.data.shape_keys.animation_data_create()
                    ob.data.shape_keys.animation_data.action = target_action

            if self.bake_to_control_rig:
                bpy.ops.faceit.bake_shape_keys_to_control_rig(
                    'INVOKE_DEFAULT',
                    action_source=target_action.name,
                    action_target='NEW',
                    new_action_name=self.new_name+CRIG_ACTION_SUFFIX,
                    compensate_amplify_values=True,
                    remove_sk_action=True,
                )
        else:
            self.report(
                {'ERROR'},
                'Something went wrong during retargeting of the new action. Is the Mapping List initialized properly?')
            bpy.data.actions.remove(target_action)

        for region in context.area.regions:
            # if region.type == 'UI':
            region.tag_redraw()

        return{'FINISHED'}


class FACEIT_OT_SetFBXActiveTargetShapes(bpy.types.Operator):
    ''' De-/Activate specified target expression '''
    bl_idname = 'faceit.set_fbx_active_target_shapes'
    bl_label = 'Activate'
    bl_options = {'UNDO', 'INTERNAL'}

    active: BoolProperty(
        default=False,
        options={'SKIP_SAVE', }
    )

    inverse: BoolProperty(
        name='Invert',
        default=False,
        options={'SKIP_SAVE', }
    )

    @ classmethod
    def poll(self, context):
        return True

    def execute(self, context):

        scene = context.scene
        retarget_list = scene.faceit_retarget_fbx_mapping

        for shape_item in retarget_list:

            if self.inverse:
                shape_item.use_animation = not shape_item.use_animation
                continue

            shape_item.use_animation = self.active

        return{'FINISHED'}


class FACEIT_OT_EditFBXTargetShape(bpy.types.Operator):
    '''Edit target shape, add new or change selected'''
    bl_label = "Add Target Shape"
    bl_idname = 'faceit.edit_fbx_target_shape'
    bl_options = {'UNDO'}

    operation: EnumProperty(
        name='Operation to perform',
        items=(
            ('ADD', 'ADD', 'ADD'),
            ('CHANGE', 'CHANGE', 'CHANGE'),
        ),
        default='ADD',
        options={'SKIP_SAVE', },

    )

    # Has to be named type for invoke_search_popup to work... wtf
    type: EnumProperty(
        items=sk_utils.get_shape_keys_from_faceit_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    index: IntProperty(
        name='Index of the Shape Item',
        default=0,
    )

    target_shape_index: IntProperty(
        name='Index of the target shape',
        default=0,
    )

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_fbx_mapping.mapping_list

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):

        # check if target shapes have been assigend to other shape items....
        retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping
        retarget_list = retarget_fbx_props.mapping_list

        shape_item = retarget_list[self.index]
        target_shapes = shape_item.target_shapes

        if shape_item:

            # Check if the target shape (type) is already assigned
            if rutils.is_target_shape_double(self.type, retarget_list):

                source_shape = ''
                for _shape_item in retarget_list:

                    if self.type in _shape_item.target_shapes:

                        source_shape = _shape_item.name

                self.report(
                    {'WARNING'},
                    'WARNING! The shape {} is already assigned to Source Shape {}'.format(
                        self.type, source_shape))
                # return {'CANCELLED'}

            if self.operation == 'CHANGE':
                if target_shapes and self.target_shape_index != -1:
                    item = target_shapes[self.target_shape_index]
                    if item:
                        item.name = self.type
            else:
                target_shape_count = len(shape_item.target_shapes)
                item = target_shapes.add()
                item.name = self.type
                item.index = target_shape_count
                item.parent_idx = shape_item.index

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


class FACEIT_OT_RemoveFBXTargetShape(bpy.types.Operator):
    bl_label = 'Remove Target Shape'
    bl_idname = 'faceit.remove_fbx_target_shape'

    parent_index: IntProperty(
        name='Index of the Shape Item',
        default=0,
    )
    target_shape_index: IntProperty(
        name='Index of the Target Shape',
        default=0,
    )

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_fbx_mapping.mapping_list

    def execute(self, context):
        scene = context.scene
        retarget_fbx_props = scene.faceit_retarget_fbx_mapping
        retarget_list = retarget_fbx_props.mapping_list

        shape_item = retarget_list[self.parent_index]

        if self.target_shape_index != -1:

            shape_item.target_shapes.remove(self.target_shape_index)

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


class FACEIT_OT_ClearFBXTargetShapes(bpy.types.Operator):
    bl_label = 'Clear Target Shape'
    bl_idname = 'faceit.clear_fbx_target_shapes'

    source_shape_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_fbx_mapping.mapping_list

    def execute(self, context):
        scene = context.scene
        retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping
        retarget_list = retarget_fbx_props.mapping_list

        shape_item = None
        try:
            shape_item = retarget_list[self.source_shape_name]
        except:
            self.report({'ERROR'}, 'Can\'t find shape {}'.format(self.source_shape_name))

        if shape_item:

            shape_item.target_shapes.clear()

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}
