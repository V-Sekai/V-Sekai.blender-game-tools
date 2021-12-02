
import os
import bpy
import json
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty, FloatProperty

from . import detection_manager
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from . import retarget_list_utils as rutils
from ..core import shape_key_utils as sk_utils


class FACEIT_OT_InitRetargeting(bpy.types.Operator):
    '''Initialize the retargeting list and try to match shapes automatically'''
    bl_idname = 'faceit.init_retargeting'
    bl_label = 'Smart Match'
    bl_options = {'UNDO', 'INTERNAL'}

    levenshtein_ratio: FloatProperty(
        name='Similarity Ratio',
        default=1.0,
        description='The ratio can be used for fuzzy name comparison. Default: 1.0'
    )

    standart_shapes: BoolProperty(
        name='Standart',
        default=False,
        description='Register for ARKit Standart Names',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    empty: BoolProperty(
        name='Empty',
        default=False,
        description='Register with Empty Targets',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    remove_prefix_target: StringProperty(
        name='Remove Prefix (Target)',
        description='Specify a Prefix in Shape Key names that will be ignore during ARKIT Shape matching.'
    )
    remove_suffix_target: StringProperty(
        name='Remove Suffix (Target)',
        description='Specify a Suffix in Shape Key names that will be ignore during ARKIT Shape matching.'
    )

    @classmethod
    def poll(self, context):
        return True

    def invoke(self, context, event):
        if self.empty == False and self.standart_shapes == False:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):

        scene = context.scene
        retarget_list = scene.faceit_retarget_shapes

        name_scheme = scene.faceit_retargeting_naming_scheme

        faceit_objects = futils.get_faceit_objects_list()
        shape_key_names = sk_utils.get_shape_key_names_from_objects(faceit_objects)

        if not shape_key_names:
            self.report({'WARNING'}, 'the registered object have no shape keys.')
            return{'CANCELLED'}

        match_names = {}
        new_names = []
        if self.remove_prefix_target or self.remove_suffix_target:
            new_names = []
            for name in shape_key_names:
                name_match = name
                if self.remove_prefix_target:
                    if name.startswith(self.remove_prefix_target):
                        name_match = name[len(self.remove_prefix_target):]
                if self.remove_suffix_target:
                    if name.endswith(self.remove_suffix_target):
                        name_match = name[:-len(self.remove_suffix_target)]
                new_names.append(name_match)
                match_names[name_match] = name

        if name_scheme == 'ARKIT':
            shape_dict = fdata.get_arkit_shape_data()
        elif name_scheme == 'FACECAP':
            shape_dict = fdata.get_face_cap_shape_data()

        retarget_list.clear()
        missing_shapes = []

        for arkit_name, data in shape_dict.items():

            # Get all target shapes to avoid double assignments

            index = data['index']
            display_name = data['name']

            item = retarget_list.add()

            item.name = arkit_name
            # item.original_arkit_name = arkit_name
            item.display_name = display_name

            item.index = index

            if self.empty:
                continue
            target_shape_count = len(item.target_shapes)

            if self.standart_shapes:
                target_item = item.target_shapes.add()
                target_item.parent_idx = index
                target_item.name = arkit_name
                target_item.index = target_shape_count
                continue

            if display_name in shape_key_names:
                target_item = item.target_shapes.add()
                target_item.parent_idx = index
                target_item.name = display_name
                shape_key_names.remove(display_name)
                target_item.index = target_shape_count
                continue
            else:
                if new_names:
                    found_shape = detection_manager.detect_shape(
                        new_names,
                        display_name,
                        min_levenshtein_ratio=self.levenshtein_ratio,
                        remove_suffix=self.remove_suffix_target,
                    )
                    found_shape = match_names.get(found_shape)
                    print(found_shape)
                else:
                    found_shape = detection_manager.detect_shape(
                        shape_key_names,
                        display_name,
                        min_levenshtein_ratio=self.levenshtein_ratio,
                        remove_suffix=self.remove_suffix_target,
                    )
                if found_shape:

                    target_item = item.target_shapes.add()
                    target_item.parent_idx = index
                    target_item.index = target_shape_count
                    target_item.name = found_shape
                    shape_key_names.remove(found_shape)
                    continue

            missing_shapes.append(display_name)

        if missing_shapes:
            for shape in reversed(missing_shapes):
                self.report({'WARNING'}, 'Couldn\'t find target shape for ARKit expression {}'.format(shape))

        for region in context.area.regions:
            # if region.type == 'UI':
            region.tag_redraw()

        return{'FINISHED'}


class FACEIT_OT_ChangeNameScheme(bpy.types.Operator):
    '''Change the retargeting list name scheme'''
    bl_idname = 'faceit.change_retargeting_name_scheme'
    bl_label = 'Change Naming Scheme'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):

        scene = context.scene
        retarget_list = scene.faceit_retarget_shapes

        name_scheme = scene.faceit_retargeting_naming_scheme

        if name_scheme == 'ARKIT':
            shape_dict = fdata.get_arkit_shape_data()
        elif name_scheme == 'FACECAP':
            shape_dict = fdata.get_face_cap_shape_data()

        for arkit_name, data in shape_dict.items():

            index = data['index']
            display_name = data['name']

            found_item = retarget_list[arkit_name]

            found_item.display_name = display_name
            # assign the new index
            found_item.index = index

        # Sort by new indices (bubble sort)
        for passesLeft in range(len(retarget_list)-1, 0, -1):
            for index in range(passesLeft):
                if retarget_list[index].index > retarget_list[index + 1].index:
                    retarget_list.move(index, index + 1)

        return{'FINISHED'}


class FACEIT_OT_RetargetNames(bpy.types.Operator):
    '''Apply the ARKit names to the specified Shape Keys'''
    bl_idname = 'faceit.retarget_names'
    bl_label = 'Apply Source Naming'
    bl_description = 'Applies the names from the source shapes to the target shape keys on all registered objects.'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        # return context.mode != 'POSE'
        return True
        # if context.mode == 'OBJECT':
        #     return context.scene.faceit_retarget_shapes

    def execute(self, context):

        scene = context.scene
        faceit_objects = futils.get_faceit_objects_list()
        retarget_list = scene.faceit_retarget_shapes

        # old_name, new_name
        rename_dict = {}

        # for i in range(len(faceit_objects)):
        for obj in faceit_objects:

            if not sk_utils.has_shape_keys(obj):
                continue
            shape_keys = obj.data.shape_keys.key_blocks

            for item in retarget_list:

                target_shapes = item.target_shapes

                if not target_shapes:
                    continue

                target_shape_item = None

                try:
                    target_shape_item = target_shapes[item.target_list_index]
                except:
                    target_shape_item = target_shapes[0]

                if not target_shape_item:
                    continue

                display_name = item.display_name

                sk = shape_keys.get(target_shape_item.name)
                if sk:
                    sk.name = display_name
                else:
                    self.report({'WARNING'}, 'Did not find shape {}'.format(target_shape_item.name))

                if obj == faceit_objects[-1]:
                    target_shape_item.name = display_name

        return{'FINISHED'}


class FACEIT_OT_ImportRetargetMap(bpy.types.Operator):
    '''Import a Retargeting Map from file. JSON file containing source and target shapes'''
    bl_idname = "faceit.import_retargeting_map"
    bl_label = 'Import'

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default='retargeting_preset.json')
    filter_glob: StringProperty(
        default='*.json;',
        options={'HIDDEN'},
    )

    @classmethod
    def poll(cls, context):
        obj = futils.get_main_faceit_object()
        if obj:
            return sk_utils.has_shape_keys(obj)

    def invoke(self, context, event):
        self.filepath = 'retargeting_preset.json'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        scene = bpy.context.scene

        filename, extension = os.path.splitext(self.filepath)
        if extension != '.json':
            self.report({'ERROR'}, 'You need to provide a file of type .json')
            return{'CANCELLED'}

        bpy.ops.faceit.init_retargeting('EXEC_DEFAULT', empty=True)

        retarget_list = scene.faceit_retarget_shapes

        try:

            with open(self.filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for arkit_name, target_dict in data.items():
                        target_shapes_list = target_dict['target_shapes']
                        shape_item = None
                        try:
                            shape_item = retarget_list[arkit_name]
                        except:
                            continue
                            pass
                        target_shapes = shape_item.target_shapes
                        shape_item.amplify = target_dict.get('amplify', 1.0)
                        # clear
                        target_shapes.clear()
                        for i, target_shape in enumerate(target_shapes_list):
                            if target_shape not in ('', '---', 'SKIP'):
                                item = target_shapes.add()
                                item.index = i
                                item.parent_idx = shape_item.index
                                item.name = target_shape

        except:
            self.report({'ERROR'}, 'Failed! Could not import from the template {}'.format(self.filepath))
            return {'CANCELLED'}

        target_shapes = rutils.get_all_set_target_shapes(retarget_list)
        if target_shapes:
            scene_shape_keys = sk_utils.get_shape_key_names_from_objects()
            shapes_not_found = [s for s in target_shapes if s not in scene_shape_keys]
            if shapes_not_found:
                self.report(
                    {'WARNING'},
                    'Following shapes could not be found in target shape keys: {}'.format(shapes_not_found))
            else:
                self.report({'INFO'}, 'Succesfully Imported {}'.format(self.filepath))
        else:
            self.report({'ERROR'}, 'Failed! Could not import from the template {}'.format(self.filepath))
            return {'CANCELLED'}

        return {'FINISHED'}


class FACEIT_OT_ExportRetargetMap(bpy.types.Operator):
    '''Export mapping to JSON file, containing source and target shapes'''
    bl_idname = "faceit.export_retargeting_map"
    bl_label = 'Export'
    bl_options = {'UNDO'}

    filepath: StringProperty(
        subtype="FILE_PATH",
        default='json'
    )

    filter_glob: StringProperty(
        default='*.json;',
        options={'HIDDEN'},
    )

    @classmethod
    def poll(cls, context):
        retarget_list = context.scene.faceit_retarget_shapes
        if retarget_list:
            if any([item.target_shapes for item in retarget_list]):
                return True

    def invoke(self, context, event):
        self.filepath = 'retargeting_preset.json'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        scene = bpy.context.scene

        retarget_list = scene.faceit_retarget_shapes

        data = {}
        shape_dict = rutils.get_target_shapes_dict(retarget_list, force_empty_strings=True)

        for arkit_name, target_shape_list in shape_dict.items():
            shape_item = retarget_list[arkit_name]
            data[arkit_name] = {
                'amplify': getattr(shape_item, 'amplify', 1.0),
                'target_shapes': target_shape_list,
            }

        if not data:
            self.report({'ERROR'}, 'Export Failed. Could not find retarget data')

        if not self.filepath.endswith('.json'):
            self.filepath += '.json'

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            self.report({'ERROR'}, 'Export Failed')
            return {'CANCELLED'}

        self.report({'INFO'}, 'Exported to {}'.format(self.filepath))

        return {'FINISHED'}


class FACEIT_OT_SetActiveShapeKeyIndex(bpy.types.Operator):
    '''Set target shape as active shape key index on all registered objects. Set to 1 if Show Only Active is true'''
    bl_idname = 'faceit.set_active_shape_key_index'
    bl_label = 'Set Active Shape Key'
    bl_options = {'UNDO', 'INTERNAL'}

    debug: BoolProperty()

    shape_name: StringProperty(
        name='Shape Key Name',
        description='The Shape Key to set active! If get arkit_target_shapes is true then this will be evaluated as a ARKit source shape',
        default='',
        options={'SKIP_SAVE'}
    )

    get_arkit_target_shapes: BoolProperty(
        name='Get Target Shapes',
        description='try to get the arkit target shapes from the arkit_shapes_list',
        default=False
    )

    @ classmethod
    def poll(self, context):
        return True  # context.scene.faceit_retarget_shapes

    def execute(self, context):

        scene = context.scene
        store_auto_kf = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        faceit_objects = futils.get_faceit_objects_list()

        if self.get_arkit_target_shapes:

            retarget_list = scene.faceit_retarget_shapes
            if self.shape_name:
                active_shape_item = retarget_list.get(self.shape_name)
            else:
                active_shape_item = retarget_list[scene.faceit_retarget_shapes_index]

            target_shapes = [item.name for item in active_shape_item.target_shapes]
        else:
            target_shapes = [self.shape_name]

        lock_active = scene.faceit_shape_key_lock

        if not target_shapes:
            self.report({'ERROR'}, 'Did not find the Shape Key(s) {}'.format(target_shapes))
            return{'CANCELLED'}

        for obj in faceit_objects:
            if not sk_utils.has_shape_keys(obj):
                continue
            shapekeys = obj.data.shape_keys.key_blocks

            # Set only one shape active per object. (First in target shapes)
            _set_active = False

            if lock_active:
                for sk in shapekeys:
                    sk.value = 0

            for target_shape_name in target_shapes:

                found_index = shapekeys.find(target_shape_name)

                if found_index != -1:

                    if not _set_active:
                        obj.active_shape_key_index = found_index
                        _set_active = True

                    if lock_active:
                        shapekeys[found_index].value = 1

        scene.tool_settings.use_keyframe_insert_auto = store_auto_kf

        return{'FINISHED'}


class FACEIT_OT_SetActiveTargetShapes(bpy.types.Operator):
    ''' De-/Activate specified target expression '''
    bl_idname = 'faceit.set_active_target_shapes'
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
        retarget_list = scene.faceit_retarget_shapes

        for shape_item in retarget_list:

            if self.inverse:
                shape_item.use_animation = not shape_item.use_animation
                continue

            shape_item.use_animation = self.active

        return{'FINISHED'}


class FACEIT_OT_EditTargetShape(bpy.types.Operator):
    '''Edit target shape, add new or change selected'''
    bl_label = "Add Target Shape"
    bl_idname = 'faceit.edit_target_shape'
    bl_property = 'all_shapes'
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
    all_shapes: EnumProperty(
        items=sk_utils.get_shape_keys_from_faceit_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    index: IntProperty(
        name='Index of the Shape Item',
        default=0,
    )

    target_shape_index: IntProperty(
        name='Index of the target shape',
        default=-1,
    )

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_shapes

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):

        # check if target shapes have been assigend to other shape items....
        shape_item = context.scene.faceit_retarget_shapes[self.index]
        target_shapes = shape_item.target_shapes
        retarget_list = context.scene.faceit_retarget_shapes

        if shape_item:

            # Check if the target shape (type) is already assigned
            if rutils.is_target_shape_double(self.all_shapes, retarget_list):
                # pass
                source_shape = ''
                for _shape_item in retarget_list:

                    if self.all_shapes in _shape_item.target_shapes:

                        source_shape = _shape_item.name

                self.report(
                    {'WARNING'},
                    'WARNING! The shape {} is already assigned to Source Shape {}'.format(
                        self.all_shapes, source_shape))
                # return {'CANCELLED'}

            if self.operation == 'CHANGE':
                if target_shapes and self.target_shape_index != -1:
                    item = target_shapes[self.target_shape_index]
                    if item:
                        item.name = self.all_shapes
            else:
                target_shape_count = len(shape_item.target_shapes)
                item = target_shapes.add()
                item.name = self.all_shapes
                item.index = target_shape_count
                item.parent_idx = shape_item.index

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


class FACEIT_OT_RemoveTargetShape(bpy.types.Operator):
    bl_label = 'Remove Target Shape'
    bl_idname = 'faceit.remove_target_shape'

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
        return context.scene.faceit_retarget_shapes

    def execute(self, context):
        scene = context.scene

        retarget_list = scene.faceit_retarget_shapes

        shape_item = retarget_list[self.parent_index]

        if self.target_shape_index != -1:
            for target_shape in shape_item.target_shapes:
                if target_shape.index >= self.target_shape_index:
                    target_shape.index -= 1
            shape_item.target_shapes.remove(self.target_shape_index)

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


class FACEIT_OT_ClearTargetShapes(bpy.types.Operator):
    bl_label = 'Clear Target Shape'
    bl_idname = 'faceit.clear_target_shapes'

    arkit_shape_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_shapes

    def execute(self, context):
        scene = context.scene

        shape_item = None
        try:

            shape_item = scene.faceit_retarget_shapes[self.arkit_shape_name]
        except:
            self.report({'ERROR'}, 'Can\'t find shape {}'.format(self.arkit_shape_name))

        if shape_item:

            shape_item.target_shapes.clear()

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}
