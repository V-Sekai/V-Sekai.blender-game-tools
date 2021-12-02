
import bpy
import bmesh
import textwrap

from bpy.props import BoolProperty, StringProperty

from ..core import mesh_utils
from ..core import faceit_utils as futils

WARNINGS_OUT = {
    'MIRROR': 'Object holds a MIRROR modifier. This can lead to problems in binding and/or baking! You should apply it first. If you need to preserve shape keys, check out the \'Apply Modifiers\' operator in bake tab/extra utils.',
    'VERTEX_ISLANDS': 'The Main vertex group should only be assigned to one connected surface. Please make sure that it only contains linked vertices!',
    'TRANSFORMS_ANIM': 'The Object has animation keyframes on transform channels. This might leat to problems in binding. Clear the keyframes or disable the action.',
    # 'AMBIGUOUS_TARGETS': 'Some shapes have been set as targets for other source shapes.'
}


class FACEIT_OT_CheckWarning(bpy.types.Operator):
    '''There are Warnings for this object'''
    bl_idname = 'faceit.face_object_warning_check'
    bl_label = 'Check Warnings'
    bl_options = {'INTERNAL'}

    # the name of the facial part
    item_name: StringProperty(options={'SKIP_SAVE'})

    set_show_warnings: BoolProperty(options={'SKIP_SAVE'})

    check_main: BoolProperty(options={'SKIP_SAVE'})

    def island_count(self, obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # deselect all verts:
        for f in bm.faces:
            f.select = False
        bm.select_flush(False)

        # SelectionIslands finds and stores selected and non-selected islands
        island_count = mesh_utils.SelectionIslands(bm.verts).get_island_count()

        bm.free()

        return island_count

    def all_verts_in_main_group(self, obj):
        vg = obj.vertex_groups.get('faceit_main')
        if vg:
            vlist = []
            index = vg.index
            for v in obj.data.vertices:
                if any([g.group == index for g in v.groups]):
                    continue
                else:
                    return False
            return True
        return False

    def execute(self, context):

        scene = context.scene

        if self.item_name == 'ALL':
            items = scene.faceit_face_objects
        else:
            items = [scene.faceit_face_objects[self.item_name]]

        faceit_objects = []

        any_warning = False
        found_main_part = False

        for item in items:
            obj = item.get_object()
            faceit_objects.append(obj)

            item.warnings = ''

            if item.part == 'main' and not 'faceit_main' in obj.vertex_groups:
                found_main_part = True

                if self.island_count(obj) > 1:
                    item.warnings += 'VERTEX_ISLANDS,'
                    any_warning = True

            elif 'faceit_main' in obj.vertex_groups:
                if self.all_verts_in_main_group(obj) and self.island_count(obj) > 1:
                    item.warnings += 'VERTEX_ISLANDS,'
                    any_warning = True

            if futils.get_modifiers_of_type(obj, 'MIRROR'):
                item.warnings += 'MIRROR,'
                any_warning = True

            if obj.animation_data:
                if obj.animation_data.action:
                    for fc in obj.animation_data.action.fcurves:
                        if any([a in fc.data_path
                                for a in ['location', 'scale', 'rotation_euler', 'rotation_quaternion']]):
                            item.warnings += 'TRANSFORMS_ANIM'
                            any_warning = True
                            break

        if any_warning:
            if self.set_show_warnings:
                scene.faceit_show_warnings = True
            self.report({'WARNING'}, 'There could be problems with the registered geometry. Please have a look at the List')
        else:
            scene.faceit_show_warnings = False
            self.report({'INFO'}, 'No Warnings found.')

        if self.check_main and not found_main_part and not any(
                ['faceit_main' in obj.vertex_groups for obj in faceit_objects]):
            self.report({'WARNING'}, 'Main Face Vertex Island could not be found. Please assign the Main Vertex Group!')

        return{'FINISHED'}


class FACEIT_OT_DisplayWarning(bpy.types.Operator):
    '''There are Warnings for this object'''
    bl_idname = 'faceit.face_object_warning'
    bl_label = 'Faceit Geometry Warnings'
    bl_options = {'INTERNAL'}

    # the name of the facial part
    warnings: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'},)

    def draw(self, context):
        layout = self.layout
        warnings = self.warnings.split(',')

        row = layout.row()
        row.label(text='WARNINGS')

        row = layout.row(align=True)
        web = row.operator('faceit.open_web', text='Prepare Geometry', icon='QUESTION')
        web.link = 'https://faceit-doc.readthedocs.io/en/latest/prepare/'

        layout.separator()

        # self.report({'WARNING'},warn)
        for warn in warnings:
            if warn:
                row = layout.row()
                row.label(text=warn.replace('_', ' '), icon='ERROR')
                warn = WARNINGS_OUT[warn]
                for w_row in textwrap.wrap(warn, 50):
                    row = layout.row()
                    row.label(text=w_row)

        row = layout.row(align=True)
        icon_hide = 'HIDE_OFF' if context.scene.faceit_show_warnings else 'HIDE_ON'
        row.prop(context.scene, 'faceit_show_warnings', icon=icon_hide)

    def invoke(self, context, event):
        wm = context.window_manager
        return wm. invoke_popup(self)

    def execute(self, context):

        warnings = self.warnings.split(',')

        for warn in warnings:
            if warn:
                warn = self.warnings_out[warn]
                self.report({'ERROR'}, warn)

        return{'FINISHED'}
