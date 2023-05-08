
import fnmatch
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, IntProperty, StringProperty)
from bpy.types import PropertyGroup, UI_UL_list

from ..panels.draw_utils import draw_text_block


from .faceit_data import get_face_region_items
from .retarget_list_utils import (are_target_shapes_valid, get_index_of_collection_item,
                                  get_index_of_parent_collection_item, get_target_shape_keys, is_target_shape_double,
                                  set_base_regions_from_dict, target_shape_key_in_registered_objects,
                                  get_invalid_target_shapes)
from .shape_key_utils import (get_shape_key_names_from_objects,
                              get_shape_keys_from_faceit_objects_enum, set_slider_max)
from ..core.faceit_utils import get_faceit_objects_list


class TargetShapes(PropertyGroup):
    name: StringProperty(
        name='Target Shape',
        description='The Target Shape',
        default='---',
    )


def update_shape_key_ranges_based_on_amplify(self, context):
    '''Update the shape key ranges based on the amplify value'''
    if not bpy.context.preferences.addons["faceit"].preferences.dynamic_shape_key_ranges:
        return
    target_sk = get_target_shape_keys(self, objects=get_faceit_objects_list())
    id_data = self.id_data
    idx = get_index_of_collection_item(self)
    setattr(id_data, self.path_from_id().split('[')[-2] + "_index", idx)
    for sk in target_sk:
        set_slider_max(sk, value=self.amplify)
        sk.value = self.amplify


class RetargetShapesBase:
    name: StringProperty(
        name='Expression Name',
        description='(Source Shape)',
        options=set(),
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
    amplify: FloatProperty(
        name='Amplify Value',
        default=1.0,
        description='Use the Amplify Value to increasing or decreasing the motion of this expression.',
        soft_min=0.0,
        soft_max=3.0,
        min=-1.0,
        max=10.0,
        update=update_shape_key_ranges_based_on_amplify
    )
    use_animation: BoolProperty(
        name='Use Animation',
        description='If this is False, the specified expression won\'t be animated by Faceit operators.',
        default=True,
        options=set()
    )
    region: EnumProperty(
        name='Face Regions',
        items=get_face_region_items,
        options=set(),
    )


class FaceRegionsBaseProperties():
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

    def set_active_regions(self, regions_dict):
        for region, value in regions_dict.items():
            setattr(self, region, value)


class FaceRegionsBase(FaceRegionsBaseProperties, PropertyGroup):
    pass


class ResetRegionsOperatorBase:
    ''' Reset the Regions Filter to default values '''
    bl_idname = ''
    bl_label = 'Reset Regions Filter'
    bl_options = {'UNDO', 'INTERNAL'}

    @staticmethod
    def get_face_regions(context):
        return context.scene.faceit_face_regions

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        face_regions_prop = self.get_face_regions(context)

        props = [x for x in face_regions_prop.keys()]
        for p in props:
            face_regions_prop.property_unset(p)

        return{'FINISHED'}


class SetDefaultRegionsBase:
    ''' Try to set the correct regions for the source/target shapes'''
    bl_idname = ''
    bl_label = 'Set Default Regions'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        return None

    def execute(self, context):

        retarget_list = self.get_retarget_shapes()
        set_base_regions_from_dict(retarget_list)

        return {'FINISHED'}


class DrawRegionsFilterBase:
    ''' Filter the displayed expressions by face regions. '''
    bl_label = "Filter Regions"

    @staticmethod
    def get_face_regions(context):
        return context.scene.faceit_face_regions

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):

        layout = self.layout
        face_regions = self.get_face_regions(context)

        col = layout.column(align=True)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.brows else 'HIDE_ON'
        row.prop(face_regions, 'brows', icon=icon_value)
        icon_value = 'HIDE_OFF' if face_regions.eyes else 'HIDE_ON'
        row.prop(face_regions, 'eyes', icon=icon_value)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.cheeks else 'HIDE_ON'
        row.prop(face_regions, 'cheeks', icon=icon_value)
        icon_value = 'HIDE_OFF' if face_regions.nose else 'HIDE_ON'
        row.prop(face_regions, 'nose', icon=icon_value)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.mouth else 'HIDE_ON'
        row.prop(face_regions, 'mouth', icon=icon_value)
        icon_value = 'HIDE_OFF' if face_regions.tongue else 'HIDE_ON'
        row.prop(face_regions, 'tongue', icon=icon_value)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.other else 'HIDE_ON'
        row.prop(face_regions, 'other', icon=icon_value)

    def execute(self, context):
        return{'FINISHED'}


class RetargetingBase:

    # the edit target shapes operator
    edit_target_shapes_operator = ''
    # the remove target shapes operator
    remove_target_shapes_operator = ''
    # the clear target shapes operator
    clear_target_shapes_operator = ''

    @classmethod
    def poll(cls, context):
        return cls.get_retarget_shapes()

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        return None


class RetargetShapesListBase():

    edit_target_shapes_operator = ''
    draw_target_shapes_operator = ''
    clear_target_shapes_operator = ''

    draw_region_filter_operator = ''
    reset_regions_filter_operator = ''

    show_use_animation = False
    property_name = 'name'

    show_assigned_regions: BoolProperty(
        name='Show Face Regions',
        default=False,
        description='Display and change the face regions for each expression.'
    )

    use_filter_name_reverse: BoolProperty(
        name="Reverse Name",
        default=False,
        options=set(),
        description="Reverse name filtering",
    )

    def draw_active(self, item):
        ''' If the return statement is false the row is drawn deactivated '''
        return bool(item.use_animation and item.target_shapes)

    def get_display_text_target_shapes(self, item):
        display_text = '---'
        if item.target_shapes:
            display_text = ', '.join([t.name for t in item.target_shapes])
        return display_text

    @staticmethod
    def get_face_regions(context):
        return context.scene.faceit_face_regions

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        self.use_filter_show = True

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            target_shapes_valid = are_target_shapes_valid(item)
            row = layout.row(align=True)
            cols = row.split(factor=0.5)
            first_col = cols.row(align=False)
            first_col.enabled = target_shapes_valid
            split = first_col.split(factor=0.7, align=True)
            name = getattr(item, self.property_name)
            split.label(text=name)
            split.prop(item, 'amplify', emboss=True, text="")
            second_col = cols.row(align=True)
            if item.target_shapes:
                second_col.alert = not target_shapes_valid
            op = second_col.operator(self.draw_target_shapes_operator, text=self.get_display_text_target_shapes(item),
                                     emboss=True, icon='DOWNARROW_HLT')
            op.source_shape = item.name

            third_col = row.row(align=True)

            op = third_col.operator(self.edit_target_shapes_operator, text='', icon='ADD')
            op.source_shape_index = get_index_of_collection_item(item)

            third_col.operator(self.clear_target_shapes_operator, text='', icon='TRASH').source_shape_name = item.name

            if self.show_assigned_regions:
                second_col.prop(item, 'region', text='')

    def draw_filter(self, context, layout):

        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop(self, "filter_name", text="")
        row.prop(self, "use_filter_name_reverse", text="", icon='ARROW_LEFTRIGHT')

        row.separator()

        row.prop(self, 'use_filter_sort_alpha', text='')
        if self.use_filter_sort_reverse:
            icon = 'SORT_DESC'
        else:
            icon = 'SORT_ASC'
        row.prop(self, "use_filter_sort_reverse", text="", icon=icon)

        row.separator()

        face_regions = self.get_face_regions(context)
        depress = any([x is False for x in face_regions.values()])
        row.operator(self.draw_region_filter_operator, depress=depress, icon='USER')
        row.operator(self.reset_regions_filter_operator, text='', icon='LOOP_BACK')

        row.separator()

        row.prop(self, 'show_assigned_regions', text='', icon='COLLAPSEMENU')  # 'PREFERENCES')

    def filter_items_in_active_regions(self, context, bitflag, items, region_dict=None, flags=None, reverse=False):
        ''' Filter all shape items and return a list where all hidden region items are marked True and all visible are marked False'''

        if not region_dict or not items:
            return flags or []

        if not flags:
            flags = [0] * len(items)

        for i, item in enumerate(items):
            if region_dict.get(item.region.lower(), False):
                flags[i] |= bitflag

        return flags

    def filter_items_by_name(self, pattern, bitflag, items, propname="name", flags=None, reverse=False):
        """
        Set FILTER_ITEM for items which name matches filter_name one (case-insensitive).
        pattern is the filtering pattern.
        propname is the name of the string property to use for filtering.
        flags must be a list of integers the same length as items, or None!
        return a list of flags (based on given flags if not None),
        or an empty list if no flags were given and no filtering has been done.
        """

        if not pattern or not items:  # Empty pattern or list = no filtering!
            return flags or []

        if flags is None:
            flags = [0] * len(items)

        # Implicitly add heading/trailing wildcards.
        pattern = "*" + pattern + "*"

        for i, item in enumerate(items):
            name = getattr(item, propname, None)
            # This is similar to a logical xor
            if bool(name and fnmatch.fnmatch(name, pattern)) is not bool(reverse):
                flags[i] &= bitflag
            else:
                flags[i] = 0
        return flags

    def filter_items(self, context, data, propname):
        ''' Filter and order items in a list '''
        # This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        # * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
        #   matching item as filtered (i.e. to be shown), and 31 other bits are free for custom needs. Here we use the
        #   first one to mark VGROUP_EMPTY.
        # * The second one is for reordering, it must return a list containing the new indices of the items (which
        #   gives us a mapping org_idx -> new_idx).
        # Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        # If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        # returning full lists doing nothing!).

        items = getattr(data, propname)
        helper_funcs = UI_UL_list

        filtered = []
        ordered = []

        face_regions = self.get_face_regions(context)
        active_region_dict = face_regions.get_active_regions()

        if any(x is True for x in active_region_dict.values()):
            filtered = self.filter_items_in_active_regions(
                context, self.bitflag_filter_item, items, region_dict=active_region_dict)

        filtered = self.filter_items_by_name(self.filter_name, self.bitflag_filter_item, items, "name",
                                             flags=filtered, reverse=self.use_filter_name_reverse)

        # Reorder by name or average weight.
        if self.use_filter_sort_alpha:
            ordered = helper_funcs.sort_items_by_name(items, "name")

        return filtered, ordered


class TargetShapesListBase:

    # the edit target shapes operator
    edit_target_shapes_operator = ''
    # the edit target shapes operator
    remove_target_shapes_operator = ''

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            layout.use_property_split = True
            layout.use_property_decorate = False
            row = layout.row(align=True)
            row.prop(item, 'name', text='', emboss=False)
            op = row.operator(self.edit_target_shapes_operator, text='', icon='DOWNARROW_HLT')
            op.operation = 'CHANGE'
            # Parent index
            source_shape_index = get_index_of_parent_collection_item(item)
            op.source_shape_index = source_shape_index
            op.target_shape = item.name
            op = row.operator(self.remove_target_shapes_operator, text='', icon='X')
            op.source_shape_index = source_shape_index
            op.target_shape = item.name


class DrawTargetShapesListBase(RetargetingBase):
    '''Mixin-Class that draws target shapes'''
    bl_label = "Target Shapes"
    bl_idname = ''

    target_shape_edit: EnumProperty(
        items=get_shape_keys_from_faceit_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    source_shape: StringProperty(
        name='Name of the Source Expression',
        default='',
    )

    # the edit target shapes operator
    edit_target_shapes_operator = ''
    # the list class name
    target_shapes_list = ''
    # Display name is used in the arkit shapes list to show the face cap names
    use_display_name = True

    @classmethod
    def poll(cls, context):
        return cls.get_retarget_shapes()

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):
        layout = self.layout
        retarget_list = self.get_retarget_shapes()
        shape_item = retarget_list[self.source_shape]
        shape_item_index = retarget_list.find(self.source_shape)
        row = layout.row()
        if self.use_display_name:
            row.label(text='Source Shape: {}'.format(shape_item.display_name))
        else:
            row.label(text='Source Shape: {}'.format(shape_item.name))
        row = layout.row()
        row.template_list(self.target_shapes_list, '', shape_item,
                          'target_shapes', shape_item, 'target_list_index')
        row = layout.row()
        op = row.operator(self.edit_target_shapes_operator, text='Add Target Shape', icon='ADD')
        op.source_shape_index = shape_item_index
        missing_target_shapes = get_invalid_target_shapes(shape_item)
        if missing_target_shapes:
            draw_text_block(
                layout=layout,
                text=f"Missing Target Shapes: {missing_target_shapes}",
                draw_in_op=True,
                alert=True
            )

    def execute(self, context):
        return{'FINISHED'}


class EditTargetShapeBase(RetargetingBase):
    '''Edit target shape, add new or change selected'''
    bl_label = "Add Target Shape"
    bl_idname = ''
    bl_property = 'new_target_shape'
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
    new_target_shape: EnumProperty(
        items=get_shape_keys_from_faceit_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    source_shape_index: IntProperty(
        name='Index of the Shape Item',
        default=0,
    )

    target_shape: StringProperty(
        name='Name of the target shape to edit',
        default='',
    )

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):
        # check if target shapes have been assigend to other shape items....
        retarget_list = self.get_retarget_shapes()
        shape_item = retarget_list[self.source_shape_index]
        target_shapes = shape_item.target_shapes
        target_shape_index = target_shapes.find(self.target_shape)
        if shape_item:
            # Check if the target shape (type) is already assigned
            if is_target_shape_double(self.new_target_shape, retarget_list):
                source_shape = ''
                for _shape_item in retarget_list:
                    if self.new_target_shape in _shape_item.target_shapes:
                        source_shape = _shape_item.name
                self.report(
                    {'WARNING'},
                    'WARNING! The shape {} is already assigned to Source Shape {}'.format(
                        self.new_target_shape, source_shape))
            if self.operation == 'CHANGE':
                if target_shapes and target_shape_index != -1:
                    item = target_shapes[target_shape_index]
                    if item:
                        item.name = self.new_target_shape
            else:
                item = target_shapes.add()
                item.name = self.new_target_shape
        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


class RemoveTargetShapeBase(RetargetingBase):
    bl_label = 'Remove Target Shape'
    bl_idname = ''

    source_shape_index: IntProperty(
        name='Index of the Shape Item',
        default=0,
    )

    target_shape: StringProperty(
        name='Index of the Target Shape',
        default='',
    )

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def execute(self, context):
        retarget_list = self.get_retarget_shapes()
        source_item = retarget_list[self.source_shape_index]
        target_shapes = source_item.target_shapes
        target_shape_index = target_shapes.find(self.target_shape)
        if target_shape_index != -1:
            source_item.target_shapes.remove(target_shape_index)
        for region in context.area.regions:
            region.tag_redraw()
        return{'FINISHED'}


class ClearTargetShapeBase(RetargetingBase):
    bl_label = 'Clear Target Shape'
    bl_idname = ''

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    source_shape_name: StringProperty()

    def execute(self, context):
        retarget_list = self.get_retarget_shapes()
        shape_item = None
        try:
            shape_item = retarget_list[self.source_shape_name]
        except KeyError:
            self.report({'ERROR'}, f'Can\'t find shape {self.source_shape_name}')
            return{'CANCELLED'}
        if shape_item:
            shape_item.target_shapes.clear()
        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}
