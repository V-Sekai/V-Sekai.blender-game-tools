import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty

from ..core import mesh_utils
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


class FACEIT_OT_AssignGroup(bpy.types.Operator):
    ''' Register the respective vertices in Edit Mode.'''
    bl_idname = 'faceit.assign_group'
    bl_label = 'Assign Vertex Group'
    bl_options = {'UNDO', 'INTERNAL'}

    # the name of the facial part
    vertex_group: bpy.props.StringProperty(
        name='vertex group',
        options={'SKIP_SAVE'},
    )

    method: EnumProperty(
        items=(
            ('OVERWRITE', 'Overwrite', 'Overwrite Faceit Groups on selected verts'),
            ('ADD', 'Add', 'Add Group to existing Faceit Groups on selected verts'),
        ),
        default='OVERWRITE',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is not None:
            if obj.type == 'MESH' and obj.name in context.scene.faceit_face_objects:
                return (context.mode in ('EDIT_MESH', 'OBJECT'))

    def invoke(self, context, event):
        self.method = context.scene.faceit_vgroup_assign_method
        return self.execute(context)

    def execute(self, context):
        scene = context.scene

        warnings = False

        obj = context.active_object

        if len(context.selected_objects) > 1:
            self.report({'WARNING'}, 'It seems you have more than one object selected. Please select only one object.')
            return{'CANCELLED'}

        mode_save = obj.mode

        grp_name = 'faceit_' + self.vertex_group

        # UnLock all Faceit Groups!
        for grp in obj.vertex_groups:
            if 'faceit_' in grp.name:
                grp.lock_weight = False

        # get vertex selection
        if obj.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
            v_selected = [v for v in obj.data.vertices if v.select]
        else:
            v_selected = obj.data.vertices

        if not v_selected:
            self.report({'ERROR'}, 'Select vertices')
            bpy.ops.object.mode_set(mode=mode_save)
            return{'CANCELLED'}

        # Get all faceit groups including eyelashes
        all_groups = fdata.get_list_faceit_groups()

        # Remove all faceit vertex groups from the active vertex selection
        for vgroup in all_groups:
            if vgroup == grp_name:
                continue
            vg_idx = obj.vertex_groups.find(vgroup)
            if vg_idx == -1:
                # vgroup does not exist
                continue

            # does the selected verts overlap with previously assigned faceit groups?
            selected_verts_in_group = [v.index for v in v_selected if vg_idx in [vg.group for vg in v.groups]]

            if selected_verts_in_group:

                all_verts_in_group = [v.index for v in obj.data.vertices if vg_idx in [vg.group for vg in v.groups]]
                # get the actual vertex group data
                vgroup = obj.vertex_groups.get(vgroup)
                # clear eventual goups without vertices:
                if self.method == 'OVERWRITE':
                    if all_verts_in_group == selected_verts_in_group:
                        obj.vertex_groups.remove(vgroup)
                    else:
                        vgroup.remove(selected_verts_in_group)

        v_indices = [v.index for v in v_selected]

        # assign the new group
        if self.method == 'OVERWRITE':
            vg_utils.assign_vertex_grp(obj, v_indices, grp_name, overwrite=True)
        else:
            vg_utils.assign_vertex_grp(obj, v_indices, grp_name, overwrite=False)

        # vg_utils.remove_zero_weights_from_verts(obj)
        # vg_utils.remove_unused_vertex_groups_thresh(obj)

        # Lock all Faceit Groups!
        for grp in obj.vertex_groups:
            if 'faceit_' in grp.name:
                grp.lock_weight = True

        if self.vertex_group == 'main':
            # Check if main group is assigned to any other object:
            faceit_objects = futils.get_faceit_objects_list()

            for _obj in faceit_objects:
                if _obj != obj:
                    vgroup = _obj.vertex_groups.get('faceit_main')
                    if vgroup:
                        _obj.vertex_groups.remove(vgroup)
                        self.report(
                            {'WARNING'},
                            'You attempted to register multiple objects as main face. Removed previous assignments of main vertex group.')
                        warnings = True

        bpy.ops.object.mode_set(mode=mode_save)

        self.report({'INFO'}, 'Assigned Vertex Group {} to the object {}.'.format(grp_name, obj.name))

        if warnings:
            self.report({'WARNING'}, 'Finished with Warnings. Please take a look at console output for more information.')

        return{'FINISHED'}


class FACEIT_OT_RemoveFaceitGroup(bpy.types.Operator):
    '''Remove Faceit group(s) from selected object'''
    bl_idname = 'faceit.remove_faceit_groups'
    bl_label = 'Reset Vertex Groups'
    bl_options = {'UNDO', 'INTERNAL'}

    # also accepts multiple groups seperated by , (e.g. 'faceit_left_eyeball,faceit_right_eyeball')
    faceit_vertex_group_names: bpy.props.StringProperty(
        name='FaceitGroup',
        default='',
        options={'SKIP_SAVE'}
    )

    object_list_index: IntProperty(
        default=-1,
        options={'SKIP_SAVE'},
    )

    all_groups: BoolProperty(
        name='Remove All Groups'
    )

    operate_scope: EnumProperty(
        name='Objects to Operate on',
        items=(
            ('ALL', 'All Objects', 'Remove all Faceit Vertex Groups from all registered Objects'),
            ('SELECTED', 'Selected Objects', 'Remove All Vertex Groups from Selected Objects in Scene'),
            # ('FACEIT', 'Selected Faceit Object', 'Remove assigned Vertex Groups from the list item Setup panel')
        ),
        default='SELECTED',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is not None:
            if obj.type == 'MESH' and obj.name in context.scene.faceit_face_objects:
                return (context.mode in ('EDIT_MESH', 'OBJECT'))

    def invoke(self, context, event):
        if self.all_groups:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, 'operate_scope', expand=True)

    def execute(self, context):

        scene = context.scene

        if self.object_list_index != -1:
            operate_objects = [futils.get_object(scene.faceit_face_objects[self.object_list_index].name)]

        elif self.operate_scope == 'ALL':
            operate_objects = [item.get_object() for item in scene.faceit_face_objects]
            self.report({'INFO'}, 'Cleared Vertex Groups for all registered objects')

        elif self.operate_scope == 'SELECTED':
            operate_objects = context.selected_objects
            if not operate_objects:
                self.report({'WARNING'}, 'You need to select at least one object for this operation to work.')
                return {'CANCELLED'}

            if len(operate_objects) > 1:
                self.report(
                    {'WARNING'},
                    'It seems you have more than one object selected. Groups will be removed from all selected objects.')

        removed_groups = {}

        if self.all_groups:
            groups_to_remove = fdata.get_list_faceit_groups()
        else:
            groups_to_remove = self.faceit_vertex_group_names.split(',')

        for grp_name in groups_to_remove:
            for obj in operate_objects:
                grp = obj.vertex_groups.get(grp_name.strip())
                if grp:
                    obj.vertex_groups.remove(grp)

                    if self.operate_scope == 'SELECTED':
                        self.report({'INFO'}, 'Removed Vertex Group {} from Object {}'.format(grp_name, obj.name))

                    else:
                        if obj.name in removed_groups:
                            removed_groups[obj.name].append(grp_name)
                        else:
                            removed_groups[obj.name] = [grp_name]
                else:
                    if self.operate_scope == 'SELECTED':
                        self.report({'INFO'}, 'The Vertex Group {} does not exist on Object {}'.format(grp_name, obj.name))

        if self.operate_scope == 'ALL':
            mssg = ''
            # for obj, grps in removed_groups.items():
            for obj in operate_objects:
                grps = removed_groups.get(obj.name)
                if grps:
                    mssg += 'Removed Groups: {} from Object: {} \n'.format(', '.join(grps), obj.name)

            if mssg:
                self.report({'INFO'}, mssg)
            else:
                self.report({'INFO'}, 'Already Cleared')

        return {'FINISHED'}


class FACEIT_OT_SelectFaceitGroup(bpy.types.Operator):
    '''Select all Vertices in the specified Faceit Vertex Group'''
    bl_idname = 'faceit.select_faceit_groups'
    bl_label = 'Select Vertices'
    bl_options = {'UNDO', 'INTERNAL'}

    faceit_vertex_group_name: bpy.props.StringProperty(
        name='FaceitGroup',
        default='',
        options={'SKIP_SAVE'}
    )

    object_list_index: IntProperty(
        default=-1,
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is not None:
            if obj.type == 'MESH' and obj.name in context.scene.faceit_face_objects:
                return (context.mode in ('EDIT_MESH', 'OBJECT'))

    def execute(self, context):

        scene = context.scene

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set()

        obj = futils.get_object(scene.faceit_face_objects[self.object_list_index].name)

        futils.clear_object_selection()
        futils.set_active_object(obj)

        vs = vg_utils.get_verts_in_vgroup(obj, self.faceit_vertex_group_name)

        mesh_utils.unselect_flush_vert_selection(obj)
        mesh_utils.select_vertices(obj, vs, flush_selection=True)

        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}
