
import json
import os

import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core.detection_manager import detect_shape
from ..core.retarget_list_base import (ClearTargetShapeBase, EditTargetShapeBase,
                                       RemoveTargetShapeBase,
                                       ResetRegionsOperatorBase,
                                       RetargetingBase, SetDefaultRegionsBase)
from ..core.retarget_list_utils import (get_all_set_target_shapes,
                                        get_target_shapes_dict,
                                        set_base_regions_from_dict)


def get_active_retarget_list():
    '''Return the active/displayed retarget list collection property.'''
    scene = bpy.context.scene
    if scene.faceit_display_retarget_list == 'ARKIT':
        return scene.faceit_arkit_retarget_shapes
    return scene.faceit_a2f_retarget_shapes


class RetargetListBase(RetargetingBase):
    @classmethod
    def poll(cls, context):
        return super().poll(context)

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        return get_active_retarget_list()


class FACEIT_OT_ResetRegions(ResetRegionsOperatorBase, bpy.types.Operator):
    bl_idname = 'faceit.reset_regions'

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_OT_EditTargetShape(EditTargetShapeBase, RetargetListBase, bpy.types.Operator):
    bl_idname = 'faceit.edit_target_shape'
    bl_property = 'new_target_shape'


class FACEIT_OT_RemoveTargetShape(RemoveTargetShapeBase, RetargetListBase, bpy.types.Operator):
    bl_idname = 'faceit.remove_target_shape'


class FACEIT_OT_ClearTargetShapes(ClearTargetShapeBase, RetargetListBase, bpy.types.Operator):
    bl_label = 'Clear Target Shape'
    bl_idname = 'faceit.clear_target_shapes'


class FACEIT_OT_SetDefaultRegions(SetDefaultRegionsBase, bpy.types.Operator):
    ''' Try to set the correct regions for the source/target shapes'''
    bl_idname = 'faceit.set_default_regions'

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        return get_active_retarget_list()

    @classmethod
    def poll(cls, context):
        return super().poll(context)


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
        name='Prefix',
        description='Specify a Prefix in Shape Key names that will be ignore during ARKIT Shape matching.'
    )
    remove_suffix_target: StringProperty(
        name='Suffix',
        description='Specify a Suffix in Shape Key names that will be ignore during ARKIT Shape matching.'
    )
    expression_sets: EnumProperty(
        name='Expression Sets',
        items=(
            ('ALL', 'All', 'Search for all available expressions'),
            ('ARKIT', 'ARKit', 'The 52 ARKit Expressions that are used in all iOS motion capture apps'),
            ('A2F', 'Audio2Face', 'The 46 expressions that are used in Nvidias Audio2Face app by default.'),
        ),
        default='ALL'
    )
    quick_search: BoolProperty(
        name="Quick Search",
        description="Only check for exact matches",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        if self.empty is False and self.standart_shapes is False:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row(align=True)
        row.label(text='Expression Sets:')
        row = box.row(align=True)
        row.prop(self, 'expression_sets', expand=True,)

        box = layout.box()
        row = box.row(align=True)
        row.label(text='Fuzzy Name Comparison:')
        row = box.row(align=True)
        row.prop(self, 'levenshtein_ratio')
        box = layout.box()
        row = box.row(align=True)
        row.label(text='Ignore in Name Comparison:')

        row = box.row(align=True)
        row.prop(self, 'remove_prefix_target')
        row = box.row(align=True)
        row.prop(self, 'remove_suffix_target')

    def execute(self, context):

        scene = context.scene

        expression_sets_dict = {}
        if self.expression_sets in ('ALL', 'ARKIT'):
            name_scheme = scene.faceit_retargeting_naming_scheme
            if name_scheme == 'ARKIT':
                expression_sets_dict['ARKIT'] = fdata.get_arkit_shape_data()
            elif name_scheme == 'FACECAP':
                expression_sets_dict['ARKIT'] = fdata.get_face_cap_shape_data()
        if self.expression_sets in ('ALL', 'A2F'):
            expression_sets_dict['A2F'] = fdata.get_a2f_shape_data()

        faceit_objects = futils.get_faceit_objects_list()
        shape_key_names = sk_utils.get_shape_key_names_from_objects(faceit_objects)

        if not shape_key_names:
            self.report({'WARNING'}, 'The registered object have no shape keys.')
            return {'CANCELLED'}

        # Remove prefix /suffix from shape names
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

        for expression_set, shape_dict in expression_sets_dict.items():
            if expression_set == 'ARKIT':
                retarget_list = scene.faceit_arkit_retarget_shapes
            else:
                retarget_list = scene.faceit_a2f_retarget_shapes

            retarget_list.clear()
            missing_shapes = []

            for expression_name, data in shape_dict.items():

                display_name = data['name']
                item = retarget_list.add()

                item.name = expression_name
                item.display_name = display_name

                if self.empty:
                    continue

                if self.standart_shapes:
                    target_item = item.target_shapes.add()
                    target_item.name = expression_name
                    continue

                if display_name in shape_key_names:
                    target_item = item.target_shapes.add()
                    target_item.name = display_name
                    shape_key_names.remove(display_name)
                    continue
                elif not self.quick_search:
                    if new_names:
                        found_shape = detect_shape(
                            new_names,
                            display_name,
                            min_levenshtein_ratio=self.levenshtein_ratio,
                            remove_suffix=self.remove_suffix_target,
                        )
                        found_shape = match_names.get(found_shape)
                        print(found_shape)
                    else:
                        found_shape = detect_shape(
                            shape_key_names,
                            display_name,
                            min_levenshtein_ratio=self.levenshtein_ratio,
                            remove_suffix=self.remove_suffix_target,
                        )
                    if found_shape:

                        target_item = item.target_shapes.add()
                        target_item.name = found_shape
                        shape_key_names.remove(found_shape)
                        continue

                missing_shapes.append(display_name)

            set_base_regions_from_dict(retarget_list)

            if missing_shapes and not self.quick_search:
                self.report(
                    {'WARNING'},
                    f'Couldn\'t find all {expression_set} target shapes. Did you generate the expressions')

        for region in context.area.regions:
            # if region.type == 'UI':
            region.tag_redraw()

        return {'FINISHED'}


class FACEIT_OT_ResetRetargetShapes(bpy.types.Operator):
    '''Clear the retarget shapes list'''
    bl_idname = 'faceit.reset_retarget_shapes'
    bl_label = 'Reset'
    bl_options = {'UNDO', 'INTERNAL'}

    expression_sets: EnumProperty(
        name='Expression Sets',
        items=(
            ('ALL', 'All', 'Search for all available expressions'),
            ('ARKIT', 'ARKit', 'The 52 ARKit Expressions that are used in all iOS motion capture apps'),
            ('A2F', 'Audio2Face', 'The 46 expressions that are used in Nvidias Audio2Face app by default.'),
        ),
        default='ALL'
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        scene = context.scene

        if self.expression_sets == 'ARKIT':
            retarget_list = scene.faceit_arkit_retarget_shapes
        else:
            retarget_list = scene.faceit_a2f_retarget_shapes

        retarget_list.clear()

        return {'FINISHED'}


class FACEIT_OT_ImportRetargetMap(bpy.types.Operator):
    '''Import a Retargeting Map from file. JSON file containing source and target shapes'''
    bl_idname = "faceit.import_retargeting_map"
    bl_label = 'Load Capture Profile'

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default='capture_profile.json')
    filter_glob: StringProperty(
        default='*.json;',
        options={'HIDDEN'},
    )
    expression_sets: EnumProperty(
        name='Expression Sets',
        items=(
            ('ARKIT', 'ARKit', 'The 52 ARKit Expressions that are used in all iOS motion capture apps'),
            ('A2F', 'Audio2Face', 'The 46 expressions that are used in Nvidias Audio2Face app by default.'),
        ),
        default='ARKIT'
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
    # @classmethod
    # def poll(cls, context):
    #     obj = futils.get_main_faceit_object()
    #     if obj:
    #         return sk_utils.has_shape_keys(obj)

    def invoke(self, context, event):
        self.filepath = 'capture_profile.json'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='Import Settings')
        row = layout.row()
        row.prop(self, 'load_amplify_values')
        row = layout.row()
        row.prop(self, 'load_regions')

    def execute(self, context):
        scene = bpy.context.scene

        _filename, extension = os.path.splitext(self.filepath)
        if extension != '.json':
            self.report({'ERROR'}, 'You need to provide a file of type .json')
            return {'CANCELLED'}

        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, f"The specified filepath does not exist: {os.path.realpath(self.filepath)}")
            return {'CANCELLED'}

        with open(self.filepath, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                if self.expression_sets == 'ARKIT':
                    if not any(x in fdata.get_arkit_shape_data().keys() for x in data.keys()):
                        self.report({'WARNING'}, 'The specified list seems to be an Audio2Face list')
                        return {'CANCELLED'}
                    retarget_list = scene.faceit_arkit_retarget_shapes
                elif self.expression_sets == 'A2F':
                    if not any(x in fdata.get_a2f_shape_data().keys() for x in data.keys()):
                        self.report({'WARNING'}, 'The specified list seems to be an ARKit list')
                        return {'CANCELLED'}
                    retarget_list = scene.faceit_a2f_retarget_shapes

                bpy.ops.faceit.init_retargeting('EXEC_DEFAULT', expression_sets=self.expression_sets, empty=True)
                default_region_dict = fdata.get_regions_dict()
                for arkit_name, target_dict in data.items():

                    target_shapes_list = target_dict['target_shapes']
                    shape_item = None
                    try:
                        shape_item = retarget_list[arkit_name]
                    except KeyError:
                        continue
                    target_shapes = shape_item.target_shapes
                    if self.load_amplify_values:
                        shape_item.amplify = target_dict.get('amplify', 1.0)
                    else:
                        shape_item.amplify = 1.0
                    if self.load_regions:
                        shape_item.region = target_dict.get('region', default_region_dict.get(shape_item.name, 'OTHER'))
                    else:
                        shape_item.region = default_region_dict.get(shape_item.name, 'OTHER')
                    # clear
                    target_shapes.clear()
                    for target_shape in target_shapes_list:
                        if target_shape not in ('', '---', 'SKIP'):
                            item = target_shapes.add()
                            item.name = target_shape

        target_shapes = get_all_set_target_shapes(retarget_list)
        if target_shapes:
            scene_shape_keys = sk_utils.get_shape_key_names_from_objects()
            shapes_not_found = [s for s in target_shapes if s not in scene_shape_keys]
            if shapes_not_found:
                self.report(
                    {'WARNING'},
                    'Following shapes could not be found in target shape keys: {}'.format(shapes_not_found))
            else:
                self.report({'INFO'}, f'Succesfully imported new {self.expression_sets} target shapes')
        else:
            self.report({'ERROR'}, 'Failed! Could not import from the template {}'.format(self.filepath))
            return {'CANCELLED'}

        return {'FINISHED'}


class FACEIT_OT_ExportRetargetMap(bpy.types.Operator):
    '''Export mapping to JSON file, containing source and target shapes'''
    bl_idname = "faceit.export_retargeting_map"
    bl_label = 'Save Capture Profile'
    bl_options = {'UNDO'}

    filepath: StringProperty(
        subtype="FILE_PATH",
        default='json'
    )

    filter_glob: StringProperty(
        default='*.json;',
        options={'HIDDEN'},
    )
    expression_sets: EnumProperty(
        name='Expression Sets',
        items=(
            ('ARKIT', 'ARKit', 'The 52 ARKit Expressions that are used in all iOS motion capture apps'),
            ('A2F', 'Audio2Face', 'The 46 expressions that are used in Nvidias Audio2Face app by default.'),
        ),
        default='ARKIT'
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

    @classmethod
    def poll(cls, context):
        retarget_list = get_active_retarget_list()
        if retarget_list:
            if any([item.target_shapes for item in retarget_list]):
                return True

    def invoke(self, context, event):
        self.filepath = 'capture_profile.json'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        retarget_list = get_active_retarget_list()
        data = {}
        shape_dict = get_target_shapes_dict(retarget_list, force_empty_strings=True)
        for arkit_name, target_shape_list in shape_dict.items():
            shape_item = retarget_list[arkit_name]
            _dict = {
                'target_shapes': target_shape_list,
            }
            if self.save_amplify_values:
                _dict['amplify'] = getattr(shape_item, 'amplify', 1.0)
            if self.save_regions:
                _dict['region'] = getattr(shape_item, 'region', 'OTHER')
            data[arkit_name] = _dict
        if not data:
            self.report({'ERROR'}, 'Export Failed. Could not find retarget data')
            return {'CANCELLED'}

        if not self.filepath.endswith('.json'):
            self.filepath += '.json'

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        self.report({'INFO'}, 'Exported to {}'.format(self.filepath))

        return {'FINISHED'}


class FACEIT_OT_SetDefaultAmplifyValues(bpy.types.Operator):
    '''Set default amplify values for all items'''
    bl_idname = 'faceit.set_default_amplify_values'
    bl_label = 'Set Default Amplify Values'
    bl_options = {'UNDO', 'INTERNAL'}

    def execute(self, context):
        retarget_list = get_active_retarget_list()
        for item in retarget_list:
            item.amplify = 1.0
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

    get_active_target_shapes: BoolProperty(
        name='Get Target Shapes',
        description='try to get the arkit target shapes from the arkit_shapes_list',
        default=False
    )
    amplify: FloatProperty(
        name='Amplify',
        default=1.0,
        options={'SKIP_SAVE'}
    )

    @ classmethod
    def poll(cls, context):
        return True  # context.scene.faceit_arkit_retarget_shapes

    def execute(self, context):

        scene = context.scene
        store_auto_kf = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        faceit_objects = futils.get_faceit_objects_list()
        # Get all possible target shapes
        all_expression_names = get_all_set_target_shapes(scene.faceit_arkit_retarget_shapes)
        all_expression_names.extend(get_all_set_target_shapes(scene.faceit_a2f_retarget_shapes))
        all_expression_names.extend([ex.name for ex in scene.faceit_expression_list])
        # Get the jawOpen shape for mouthClose evaluation
        jawOpen_item = None
        if self.get_active_target_shapes:

            if scene.faceit_display_retarget_list == 'ARKIT':
                retarget_list = scene.faceit_arkit_retarget_shapes
                retarget_list_index = scene.faceit_arkit_retarget_shapes_index
            else:
                retarget_list = scene.faceit_a2f_retarget_shapes
                retarget_list_index = scene.faceit_a2f_retarget_shapes_index
            if self.shape_name:
                active_shape_item = retarget_list.get(self.shape_name)
                if self.shape_name == 'mouthClose':
                    jawOpen_item = retarget_list.get('jawOpen')
            else:
                active_shape_item = retarget_list[retarget_list_index]

            target_shapes = [item.name for item in active_shape_item.target_shapes]
        else:
            target_shapes = [self.shape_name]

        if not target_shapes:
            # self.report({'ERROR'}, 'Did not find the Shape Key(s) {}'.format(target_shapes))
            return {'CANCELLED'}

        for obj in faceit_objects:
            if not sk_utils.has_shape_keys(obj):
                continue
            shapekeys = obj.data.shape_keys.key_blocks

            # Set only one shape active per object. (First in target shapes)
            _set_active = False

            for sk in shapekeys:
                if sk.name in all_expression_names:
                    sk.value = 0

            for target_shape_name in target_shapes:

                found_index = shapekeys.find(target_shape_name)

                if found_index != -1:

                    if not _set_active:
                        obj.active_shape_key_index = found_index
                        _set_active = True

                    if jawOpen_item is not None:
                        for _ts in jawOpen_item.target_shapes:
                            jawOpenSk = shapekeys.get(_ts.name)
                            if jawOpenSk:
                                jawOpenSk.value = jawOpen_item.amplify
                    shapekeys[found_index].value = self.amplify

        scene.tool_settings.use_keyframe_insert_auto = store_auto_kf

        return {'FINISHED'}
