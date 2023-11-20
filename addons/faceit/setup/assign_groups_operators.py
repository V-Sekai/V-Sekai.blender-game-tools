import bmesh
import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty
import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_origin_3d

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import mesh_utils
from ..core import vgroup_utils as vg_utils

import numpy as np

picker_running = False


def is_picker_running():
    global picker_running
    return picker_running


def draw_callback(self):
    if self is None:
        print("self is None")
        return
    if not self.obj:
        return
    shader = gpu.shader.from_builtin('3D_FLAT_COLOR')
    batch = batch_for_shader(
        shader, 'TRIS',
        {"pos": self.vert_data, "color": self.vertex_colors},
        indices=self.indices,
    )
    # shader.bind()
    # gpu.state.face_culling_set('BACK')
    # gpu.state.blend_set('ADDITIVE')
    gpu.state.depth_test_set('NONE')
    batch.draw(shader)


def draw_callback_blf(self):
    if self is None:
        print("self is None")
        return
    x, y = self.cursor_pos
    font_id = 0
    font_offset = 10
    blf.position(font_id, x + font_offset, y - font_offset * 2, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, self.txt)


class FACEIT_OT_AssignMainModal(bpy.types.Operator):
    ''' Register the main surface. Draws an overlay to help you select the right vertices.'''
    bl_idname = 'faceit.assign_main_modal'
    bl_label = 'Assign Main Vertex Group'
    bl_options = {'UNDO', 'INTERNAL'}

    def __init__(self):
        self._handler = None
        self._blf_handler = None
        self.dg = None
        self.obj = None
        self.bm = None
        self.mat = None
        self.vert_data = None
        self.indices = None
        self.vertex_colors = None
        self.is_faceit_obj = False
        self.obj_data_dict = {}
        self.island_ids = None
        self.geo_islands = None
        self.single_island = False
        self.cursor_pos = (0, 0)
        self.txt = "Assign Face."
        self.simplify_count = 0
        self.simplify_state = False

    @classmethod
    def poll(cls, context):
        return (context.mode in ('OBJECT', ))  # 'EDIT_MESH'

    @classmethod
    def description(self, context, properties):
        _doc_string = "Works different in Edit / Object Mode.\n"
        if context.mode == 'EDIT_MESH':
            _doc_string += "Edit Mode: Assign selected vertices to this group.\n"
        else:
            _doc_string += "Object Mode: Assign all vertices of the selected object to this group.\n"
        _doc_string += "You can assign multiple groups to one object.\n\n"
        _doc_string += "The main group: (face, skull, body, skin)\n"
        _doc_string += "This group should consist of one connected surface. In other words, all vertices assigned to this group should be linked by edges. It does not matter if this encompasses the skull or even the whole body. \n"
        _doc_string += "Read more in the Faceit documentation."
        return _doc_string

    def get_vertex_data(self, bm):
        ''' Get the relevant vertex data for the shader.'''
        self.vert_data = np.array([self.mat @ v.co for v in bm.verts], np.float32)
        self.indices = [[loop.vert.index for loop in looptris]
                        for looptris in bm.calc_loop_triangles()]

    def delete_vertices_outside_island(self, bm, island_ids):
        '''Deletes all vertices that are not in the island_ids'''
        verts_delete = [v for v in bm.verts if v.index not in island_ids]
        if verts_delete:
            bmesh.ops.delete(bm, geom=verts_delete, context='VERTS')
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

    def get_color(self, vert_count):
        '''Get the color for the shader.'''
        self.vertex_colors = [(0, 0, .9, .5) for _ in range(vert_count)]

    def get_the_hit_island(self, bm, face_index):
        '''Returns the island ids of the surface with face_index'''
        face = bm.faces[face_index]
        v_face = face.verts[0]
        for island_ids, island_bm in self.geo_islands.items():
            if v_face.index in island_ids:
                return island_ids, island_bm

    def modal(self, context, event):
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        self.cursor_pos = coord
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
        context.area.tag_redraw()
        self.dg.update()
        if event.type in {'MOUSEMOVE', 'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN',
                          'TRACKPADZOOM', 'MOUSEROTATE', 'MOUSESMARTZOOM'} or event.shift or event.ctrl or event.oskey:
            # Get the object below mouse cursor.
            result, _location, _normal, face_index, obj_hit, _matrix = self.dg.scene_eval.ray_cast(
                self.dg, ray_origin, view_vector)
            if not result or not obj_hit:
                bpy.context.window.cursor_set("DEFAULT")
                self.obj = None
                self.is_faceit_obj = False
                self.bm = None
                self.txt = "Select a Surface."
                return {'PASS_THROUGH'}
            if obj_hit.name not in self.obj_data_dict:
                bpy.context.window.cursor_set("DEFAULT")
                self.obj = None
                self.is_faceit_obj = False
                self.bm = None
                self.txt = "Object not registered."
                return {'PASS_THROUGH'}
            data_dict = self.obj_data_dict[obj_hit.name]
            if self.obj != obj_hit:
                bpy.context.window.cursor_set("EYEDROPPER")
                obj_hit = obj_hit.evaluated_get(self.dg)
                bm = data_dict['bm']
                self.bm = bm
                self.mat = obj_hit.matrix_world
                self.is_faceit_obj = data_dict['is_faceit_obj']
                self.obj = obj_hit
                self.geo_islands = data_dict['geo_islands']
                self.single_island = data_dict['single_island']
                self.txt = obj_hit.name

            if self.single_island:
                island_ids = list(self.geo_islands.keys())[0]  # Get the single island in this obj
                island_bm = list(self.geo_islands.values())[0]
            else:
                island_ids, island_bm = self.get_the_hit_island(self.bm, face_index)  # Get the island hit by ray.
            if island_ids is None:
                return {'PASS_THROUGH'}
            if island_ids != self.island_ids:
                self.island_ids = island_ids
                if not self.single_island and island_bm is None:
                    island_bm = self.bm.copy()  # data_dict['bm'].copy()
                    self.delete_vertices_outside_island(island_bm, island_ids)
                    self.geo_islands[island_ids] = island_bm
                self.get_vertex_data(island_bm)
                self.get_color(len(self.vert_data))
            return {'PASS_THROUGH'}

        elif event.type == 'LEFTMOUSE':
            # Assign Group here.
            if self.obj and self.is_faceit_obj:
                mode_save = futils.get_object_mode_from_context_mode(context.mode)
                if mode_save != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
                warning = None
                vgroup_props = bpy.context.scene.faceit_vertex_groups
                grp_prop = vgroup_props.get('faceit_main')
                if grp_prop.is_assigned:
                    for obj_name in self.obj_data_dict.keys():
                        _obj = futils.get_object(obj_name)
                        if _obj != self.obj:
                            vgroup = _obj.vertex_groups.get('faceit_main')
                            if vgroup:
                                warning = True
                                _obj.vertex_groups.remove(vgroup)
                                grp_prop.remove_object(_obj.name)
                                self.report(
                                    {'WARNING'},
                                    'Succes! Removed previous assignments of main vertex group.')
                vg_utils.assign_vertex_grp(
                    self.obj.original,
                    self.island_ids,
                    'faceit_main',
                    overwrite='REPLACE'
                )
                grp_prop.assign_object(self.obj.original.name)
                self.end(context)
                if mode_save != 'OBJECT':
                    bpy.ops.object.mode_set(mode=mode_save)
                if not warning:
                    self.report({'INFO'}, "Main group assigned.")
                return {'FINISHED'}
            elif not self.is_faceit_obj:
                self.report({'WARNING'}, "The surface needs to be part of a Faceit object.")
                return {'RUNNING_MODAL'}
            else:
                self.report({'WARNING'}, "You need to select a valid surface.")
                return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.end(context)
            self.report({'INFO'}, "Cancelled.")
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def end(self, context):
        global picker_running
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._blf_handler, 'WINDOW')
        for data_dict in self.obj_data_dict.values():
            bm = data_dict['bm']
            if bm is not None:
                bm.free()
        context.scene.render.use_simplify = self.simplify_state
        context.scene.render.simplify_subdivision = self.simplify_count
        bpy.context.window.cursor_set("DEFAULT")
        picker_running = False

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            global picker_running
            self.simplify_state = context.scene.render.use_simplify
            self.simplify_count = context.scene.render.simplify_subdivision
            context.scene.render.use_simplify = True
            context.scene.render.simplify_subdivision = 0
            self.mode_save = futils.get_object_mode_from_context_mode(context.mode)
            self.dg = context.evaluated_depsgraph_get()
            for obj in futils.get_faceit_objects_list():
                if futils.get_hide_obj(obj):
                    continue
                obj = obj.evaluated_get(self.dg)
                _is_faceit_object = obj.name in context.scene.faceit_face_objects
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                geo_islands = mesh_utils.GeometryIslands(bm.verts)
                geo_island_ids = {}  # dict containing island ids and bmesh
                if len(geo_islands.islands) == 1:
                    # convert to tuple and make immutable (hashable).
                    geo_island_ids[tuple(set([v.index for v in geo_islands.islands[0]]))] = bm
                else:
                    for island in geo_islands.islands:
                        island_ids = tuple(set([v.index for v in island]))  # remove double entries and make immutable.
                        geo_island_ids[island_ids] = None
                self.obj_data_dict[obj.name] = {
                    'bm': bm,
                    'geo_islands': geo_island_ids,
                    'is_faceit_obj': _is_faceit_object,
                    'single_island': len(geo_island_ids) == 1
                }
            args = (self,)
            self._handler = bpy.types.SpaceView3D.draw_handler_add(draw_callback, args, 'WINDOW', 'POST_VIEW')
            # For some reason gpu drawing doesn't work in POST_PIXEL and blf doesn't work in POST_VIEW.
            self._blf_handler = bpy.types.SpaceView3D.draw_handler_add(draw_callback_blf, args, 'WINDOW', 'POST_PIXEL')
            picker_running = True
            print(picker_running)
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class FACEIT_OT_AssignMain(bpy.types.Operator):
    ''' Register the respective vertices in Edit Mode or all vertices in Object Mode'''
    bl_idname = 'faceit.assign_main'
    bl_label = 'Assign Main Vertex Group'
    bl_options = {'UNDO', 'INTERNAL'}

    def __init__(self):
        self.mode_save = 'OBJECT'

    @ classmethod
    def description(self, context, properties):
        _doc_string = "Works different in Edit / Object Mode.\n"
        if context.mode == 'EDIT_MESH':
            _doc_string += "Edit Mode: Assign selected vertices to this group.\n"
        else:
            _doc_string += "Object Mode: Assign all vertices of the selected object to this group.\n"
        _doc_string += "You can assign multiple groups to one object.\n\n"
        _doc_string += "The main group: (face, skull, body, skin)\n"
        _doc_string += "This group should consist of one connected surface. In other words, all vertices assigned to this group should be linked by edges. It does not matter if this encompasses the skull or even the whole body. \n"
        _doc_string += "Read more in the Faceit documentation."
        return _doc_string
        # return 'Assign the selected vertices to the %s group' % properties.vertex_group

    @ classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is not None:
            if obj.type == 'MESH' and obj.name in context.scene.faceit_face_objects:
                return (context.mode in ('EDIT_MESH', 'OBJECT'))

    def invoke(self, context, event):
        # Check the number of selected objects.
        # Check the number of selected surfaces.
        # Expand the selection and warn the user about that.
        # Execute the assign operator (or just assign the group...)
        if len(context.selected_objects) > 1:
            self.report(
                {'ERROR'},
                'It seems you have more than one object selected. Please select only the object containing the main facial geometry.')
            return {'CANCELLED'}
        obj = context.active_object
        self.mode_save = obj.mode
        if self.mode_save == 'OBJECT':
            bm = bmesh.new()
            bm.from_mesh(obj.data)
        else:
            bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.select_flush(True)
        geo_islands = mesh_utils.GeometryIslands(bm.verts)
        if self.mode_save == 'OBJECT':
            islands = geo_islands.get_islands()
            if len(islands) > 1:
                bm.free()
                self.report(
                    {'ERROR'},
                    'There is more than one surface in the selected object. \nPlease switch to edit mode and select only the main facial surface.')
                return {'CANCELLED'}
            else:
                # make sure all verts are selected.
                for v in bm.verts:
                    v.select = True
                bm.select_flush(True)
                bm.to_mesh(obj.data)
                bm.free()
        else:
            if not any(v.select for v in bm.verts):
                bmesh.update_edit_mesh(obj.data)
                self.report({'ERROR'}, 'No vertices selected.')
                return {'CANCELLED'}
            islands = list(geo_islands.get_selected_islands())
            if len(islands) > 1:
                bmesh.update_edit_mesh(obj.data)
                self.report(
                    {'ERROR'},
                    'It seems you have more than one surface selected. Please select only the main surface.')
                return {'CANCELLED'}
            all_verts_selected = all(v.select for v in islands[0])
            if not all_verts_selected:
                # self.report(
                #     {'ERROR'},
                #     'A selection should always consist of all vertices of a surface. \nThe selection has been corrected.')
                geo_islands.select_linked()
                bm.select_flush(True)
                bmesh.update_edit_mesh(obj.data)
                return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        box = self.layout.box()
        box.label(text='Warning', icon='ERROR')
        box.label(text='The Main group should hold a connected surface.')
        box.label(text='The selection has been corrected.')
        box.label(text='Do you want to continue?')

    def execute(self, context):
        obj = context.active_object
        faceit_objects = futils.get_faceit_objects_list()
        vgroup_props = bpy.context.scene.faceit_vertex_groups
        grp_prop = vgroup_props.get('faceit_main')
        if grp_prop.is_assigned:
            for _obj in faceit_objects:
                if _obj != obj:
                    vgroup_name = _obj.vertex_groups.get('faceit_main')
                    if vgroup_name:
                        _obj.vertex_groups.remove(vgroup_name)
                        grp_prop.remove_object(_obj.name)
                        self.report(
                            {'WARNING'},
                            'You attempted to register multiple objects as main face. Removed previous assignments of main vertex group.')
        bpy.ops.object.mode_set(mode=self.mode_save)
        bpy.ops.faceit.assign_group('INVOKE_DEFAULT', vertex_group='main')
        grp_prop.assign_object(obj.name)
        self.report({'INFO'}, f'The main surface has been assigned in object {obj.name}.')
        return {'FINISHED'}


initial_selection = []
vertices_already_in_group = []


def update_selection_based_on_assing_method(self, context):
    global initial_selection, vertices_already_in_group
    if not self.vgroup_already_assigned:
        return
    obj = context.active_object
    if obj.mode == 'OBJECT':
        return
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.select_flush(True)
    if self.method == 'ADD':
        for v in bm.verts:
            if v.index in set(vertices_already_in_group + initial_selection):
                v.select = True
            else:
                v.select = False
    else:
        for v in bm.verts:
            if v.index in initial_selection:
                v.select = True
            else:
                v.select = False
    bm.select_flush(True)
    bm.select_flush(False)
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.ed.undo_push(message='Faceit: Selection changed')


class FACEIT_OT_AssignGroup(bpy.types.Operator):
    ''' Register the respective vertices in Edit Mode or all vertices in Object Mode'''
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
            ('REPLACE', 'Replace', 'Remove vertex group from selected object and assign new selection'),
            ('ADD', 'Add', 'Add selected verts to the existing vertex groups'),
        ),
        default='REPLACE',
        options={'SKIP_SAVE'},
        update=update_selection_based_on_assing_method,
    )
    vgroup_already_assigned: BoolProperty(
        name='Vertex Group Already Assigned',
        default=False,
        options={'SKIP_SAVE'},
    )

    def __init__(self):
        global initial_selection, vertices_already_in_group
        # True when any of the faceit vertex groups is assigned to the vertex selection.
        self.faceit_group_in_selection = False
        # Groups that are already assigned to the selection.
        self.faceit_groups_in_selection = []
        self.mode_save = 'OBJECT'
        # The selected vertices (indices).
        initial_selection = []
        vertices_already_in_group = []

    @ classmethod
    def description(self, context, properties):
        _doc_string = "Works different in Edit / Object Mode.\n"
        if context.mode == 'EDIT_MESH':
            _doc_string += "Edit Mode: Assign selected vertices to this group.\n"
        else:
            _doc_string += "Object Mode: Assign all vertices of the selected object to this group.\n"
        _doc_string += "You can assign multiple groups to one object.\n\n"
        # _doc_string = "Quickly assign all vertices of a selected object to a group in Object Mode or assign a selection of vertices to a group in Edit Mode.\n You can assign multiple groups within the same object. "
        if properties.vertex_group == "main":
            _doc_string += "The main group: (face, skull, body, skin)\n"
            _doc_string += "This group should consist of one connected surface. In other words, all vertices assigned to this group should be linked by edges. It does not matter if this encompasses the skull or even the whole body. \n"
        elif "eyeball" in properties.vertex_group:
            _doc_string += "Left/Right Eyeball: (spheres or half-spheres)"
        elif "eyes" in properties.vertex_group:
            _doc_string += "Left/Right Eyes: All Deform Geometry(Eyeballs, Cornea, Pupils, Iris, Highlights, smaller eye parts, etc.)"
            _doc_string += "The assigned geometry will be weighted to the respective eye bone only.\n"
        elif "teeth" in properties.vertex_group:
            _doc_string += "Teeth: (Upper & Lower Teeth, Gum, Mouth Interior, etc.)\n"
            _doc_string += "The assigned geometry will be weighted to the respective teeth bone only.\n"
        elif "eyelashes" in properties.vertex_group:
            _doc_string += "Eyelashes: (Eyelashes, Eyeshells, Tearlines, etc.)\n"
            _doc_string += "The eyelashes group will be weighted to the lid bones only. You should not assign the eyelids themselves to this group\n"
        elif "tongue" in properties.vertex_group:
            _doc_string += "Tongue: (Tongue)"
            _doc_string += "The tongue group will be weighted to the tongue bones only.\n"
        elif "rigid" in properties.vertex_group:
            _doc_string += "Rigid: (All geometry that is not supposed to deform)"
        elif "facial_hair" in properties.vertex_group:
            _doc_string += "Facial Hair: (Beard, Moustache, Sideburns, etc.)"
            _doc_string += "This group is optional. Currently, geometry that is not assigned to any group will be treated as facial hair.\n"
        _doc_string += "Read more in the Faceit documentation."
        return _doc_string

    @ classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is not None:
            if obj.select_get() is False:
                return False
            if obj.type == 'MESH' and obj.name in context.scene.faceit_face_objects:
                return (context.mode in ('EDIT_MESH', 'OBJECT'))

    def invoke(self, context, event):
        global initial_selection, vertices_already_in_group
        if len(context.selected_objects) > 1:
            self.report({'ERROR'}, 'It seems you have more than one object selected. Please select only one object.')
            return {'CANCELLED'}
        obj = context.active_object
        self.mode_save = obj.mode
        # get the selected vertices
        if obj.mode == 'EDIT':
            bpy.ops.object.mode_set()
            v_selected = [v for v in obj.data.vertices if v.select]
        else:
            v_selected = obj.data.vertices
        if not v_selected:
            self.report({'ERROR'}, 'Select vertices')
            bpy.ops.object.mode_set(mode=self.mode_save)
            return {'CANCELLED'}
        initial_selection = [v.index for v in v_selected]
        # Don't check for overlapping groups if it's the main group
        vgroup_props = context.scene.faceit_vertex_groups
        for grp_prop in vgroup_props:
            vgroup_name = grp_prop.name
            if vgroup_name == "faceit_main":
                continue
            vgroup = obj.vertex_groups.get(vgroup_name)
            if not vgroup:
                continue
            vid_in_vgroup = [v.index for v in obj.data.vertices if vgroup.index in [vg.group for vg in v.groups]]
            if self.vertex_group in vgroup_name:
                if all((vid in initial_selection for vid in vid_in_vgroup)):
                    self.report(
                        {'INFO'},
                        f'The selected vertices are already assigned to the "{self.get_clean_name(vgroup_name)}" group.')
                    # bpy.ops.object.mode_set(mode=self.mode_save)
                    # return {'CANCELLED'}
                vertices_already_in_group = vid_in_vgroup
                self.vgroup_already_assigned = True
            elif grp_prop.is_assigned:
                # Check if the faceit vertex group overlaps with the active selection
                if self.vertex_group in ("left_eyeball", "right_eyeball",):
                    continue
                if vgroup_name in ("faceit_left_eyeball", "faceit_right_eyeball",):
                    continue
                if any((vid in vid_in_vgroup for vid in initial_selection)):  # and vgroup_name != "faceit_main":
                    self.faceit_groups_in_selection.append(vgroup_name)

        if self.vgroup_already_assigned or self.faceit_groups_in_selection:
            bpy.ops.object.mode_set(mode=self.mode_save)
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        if self.vgroup_already_assigned:
            box = layout.box()
            box.label(text="WARNING", icon='ERROR')
            box.label(text='"%s" is already assigned.' % self.get_clean_name(self.vertex_group))
            box.label(text='Do you want to overwrite the existing assignment?')
            box.prop(self, 'method', expand=True)
        if self.faceit_groups_in_selection:
            box = layout.box()
            row = box.row(align=True)
            row.label(text="WARNING", icon='ERROR')
            row = box.row(align=True)
            row.label(text="The following groups will be overwritten:")
            for grp_name in self.faceit_groups_in_selection:
                box.label(text=self.get_clean_name(grp_name))

            # layout.label(text='Warning: Selection already assigned to:')
    def get_clean_name(self, name):
        '''Return a printable name for the vertex group'''
        return name.replace("faceit_", "").replace("_", " ").title()

    def execute(self, context):
        obj = context.active_object
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set()
        grp_name = 'faceit_' + self.vertex_group
        vgroup_props = context.scene.faceit_vertex_groups
        grp_prop = vgroup_props.get(grp_name)
        # UnLock all Faceit Groups!
        for grp in obj.vertex_groups:
            if 'faceit_' in grp.name:
                grp.lock_weight = False
        if self.mode_save == 'EDIT':
            v_selected = [v for v in obj.data.vertices if v.select]
        else:
            v_selected = obj.data.vertices
        # Remove all faceit vertex groups from the active vertex selection
        for vgroup_name in self.faceit_groups_in_selection:
            vgroup = obj.vertex_groups.get(vgroup_name)
            selected_verts_in_group = [v.index for v in v_selected if vgroup.index in [vg.group for vg in v.groups]]
            vgroup.remove(selected_verts_in_group)
            # Check if the group is empty now.
            if not any(vgroup.index in [g.group for g in v.groups] for v in obj.data.vertices):
                obj.vertex_groups.remove(vgroup)
                _grp_prop = vgroup_props.get(vgroup_name)
                if _grp_prop:
                    _grp_prop.remove_object(obj.name)
        # assign the new group
        vg_utils.assign_vertex_grp(
            obj,
            [v.index for v in v_selected],
            grp_name,
            overwrite=self.method == 'REPLACE'
        )
        grp_prop.assign_object(obj.name)
        vgroup = obj.vertex_groups.get(grp_name)
        # Select the new assingment
        for v in obj.data.vertices:
            if vgroup.index in [vg.group for vg in v.groups]:
                v.select = True
            else:
                v.select = False
        self.report({'INFO'}, f'Assigned Vertex Group {grp_name} to the object {obj.name}')
        if obj.mode != self.mode_save:
            bpy.ops.object.mode_set(mode=self.mode_save)
        return {'FINISHED'}


def get_objects_with_vertex_group_enum(self, context):
    global objects
    objects = []

    if context is None:
        print('Context is None')
        return objects

    # all_vgroups = vg_utils.get_vertex_groups_from_objects(objects)
    found_objects = vg_utils.get_objects_with_vertex_group(self.vgroup_name, get_all=True)
    txt = 'Remove from'
    if found_objects:
        idx = 0
        if len(found_objects) > 1:
            objects.append(('ALL', f'{txt} All Objects', 'Remove all Corrective Shape Keys for this expression', idx))
            idx += 1
        for obj in found_objects:
            name = obj.name
            objects.append((name, f'{txt}  {name}', name, idx))
            idx += 1
    else:
        objects.append(('None', 'None', 'None'))
    return objects


class FACEIT_OT_RemoveFaceitGroup(bpy.types.Operator):
    '''Remove Faceit group(s) from selected object'''
    bl_idname = 'faceit.remove_faceit_groups'
    bl_label = 'Reset Vertex Groups'
    bl_property = 'operate_objects'
    bl_options = {'UNDO', 'INTERNAL'}

    # also accepts multiple groups seperated by , (e.g. 'faceit_left_eyeball,faceit_right_eyeball')
    vgroup_name: bpy.props.StringProperty(
        name='FaceitGroup',
        default='',
        options={'SKIP_SAVE'}
    )
    operate_objects: bpy.props.EnumProperty(
        name='Operate Objects',
        items=get_objects_with_vertex_group_enum,
    )

    @ classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):

        operate_objects = []
        if self.operate_objects == 'ALL':
            operate_objects = futils.get_faceit_objects_list()
            self.report({'INFO'}, f'Removed the vertex group {self.vgroup_name} from all objects')
        else:
            obj = futils.get_object(self.operate_objects)
            operate_objects.append(obj)
            self.report({'INFO'}, f'Removed the vertex group {self.vgroup_name} from {obj.name}')
        vgroup_props = context.scene.faceit_vertex_groups
        grp_prop = vgroup_props.get(self.vgroup_name)
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.faceit.mask_group('INVOKE_DEFAULT', vgroup_name=self.vgroup_name, operation='REMOVE')
        for obj in operate_objects:
            grp = obj.vertex_groups.get(self.vgroup_name)
            if grp:
                obj.vertex_groups.remove(grp)
            grp_prop.remove_object(obj.name)
        return {'FINISHED'}


class FACEIT_OT_RemoveFaceitGroupList(bpy.types.Operator):
    '''Remove Faceit group(s) from selected object'''
    bl_idname = 'faceit.remove_faceit_group_list'
    bl_label = 'Reset Vertex Groups'
    bl_options = {'UNDO', 'INTERNAL'}

    vgroup_name: bpy.props.StringProperty(
        name='FaceitGroup',
        default='',
        options={'SKIP_SAVE'}
    )
    object_list_index: IntProperty(
        default=-1,
        options={'SKIP_SAVE'},
    )

    @ classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        if self.object_list_index != -1:
            operate_objects = [futils.get_object(scene.faceit_face_objects[self.object_list_index].name)]
        bpy.ops.faceit.mask_group('INVOKE_DEFAULT', vgroup_name=self.vgroup_name, operation='REMOVE')
        vgroup_props = context.scene.faceit_vertex_groups
        grp_prop = vgroup_props.get(self.vgroup_name)
        for obj in operate_objects:
            grp = obj.vertex_groups.get(self.vgroup_name)
            if grp:
                obj.vertex_groups.remove(grp)
                grp_prop.remove_object(obj.name)
        return {'FINISHED'}


class FACEIT_OT_RemoveAllFaceitGroups(bpy.types.Operator):
    '''Remove Faceit group(s) from selected object'''
    bl_idname = 'faceit.remove_all_faceit_groups'
    bl_label = 'Reset All Faceit Vertex Groups'
    bl_options = {'UNDO', 'INTERNAL'}

    operate_scope: EnumProperty(
        name='Objects to Operate on',
        items=(
            ('ALL', 'All Objects', 'Remove all Faceit Vertex Groups from all registered Objects'),
            ('SELECTED', 'Selected Objects', 'Remove All Vertex Groups from Selected Objects in Scene'),
        ),
        default='SELECTED',
    )

    @ classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'operate_scope', expand=True)

    def execute(self, context):
        scene = context.scene
        if self.operate_scope == 'ALL':
            operate_objects = [item.get_object() for item in scene.faceit_face_objects]
            self.report({'INFO'}, 'Cleared Vertex Groups for all registered objects')
        elif self.operate_scope == 'SELECTED':
            operate_objects = [obj for obj in context.selected_objects if obj.name in scene.faceit_face_objects]
            if not operate_objects:
                self.report({'WARNING'}, 'You need to select at least one object for this operation to work.')
                return {'CANCELLED'}
        groups_to_remove = fdata.get_list_faceit_groups()
        vgroup_props = context.scene.faceit_vertex_groups
        for grp_name in groups_to_remove:
            grp_prop = vgroup_props.get(grp_name)
            bpy.ops.faceit.mask_group('INVOKE_DEFAULT', vgroup_name=grp_name, operation='REMOVE')
            for obj in operate_objects:
                grp = obj.vertex_groups.get(grp_name)
                if grp:
                    grp_prop.remove_object(obj.name)
                    obj.vertex_groups.remove(grp)
        return {'FINISHED'}


class FACEIT_OT_SelectFaceitGroup(bpy.types.Operator):
    '''Select all Vertices in the specified Faceit Vertex Group'''
    bl_idname = 'faceit.select_faceit_groups'
    bl_label = 'Select Vertices'
    bl_options = {'INTERNAL'}

    faceit_vertex_group_name: bpy.props.StringProperty(
        name='FaceitGroup',
        default='',
        options={'SKIP_SAVE'}
    )
    object_list_index: IntProperty(
        default=-1,
        options={'SKIP_SAVE'},
    )

    @ classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        scene = context.scene
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set()
        scene.faceit_face_index = self.object_list_index
        obj = futils.get_object(scene.faceit_face_objects[self.object_list_index].name)
        if futils.get_hide_obj(obj):
            futils.set_hide_obj(obj, False)
        futils.set_active_object(obj)
        vs = vg_utils.get_verts_in_vgroup(obj, self.faceit_vertex_group_name)
        mesh_utils.select_vertices(obj, vs, deselect_others=True)
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


def draw_group_callback(self):
    '''Draws Wireframe Overlay for given verts/indices'''
    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    batch = batch_for_shader(
        shader, 'LINES', {"pos": self.vert_data},
        indices=self.indices)
    shader.uniform_float("color", (0, .8, .2, .1))

    gpu.state.depth_test_set('NONE')
    # bgl.glLineWidth(5)
    # gpu.state.line_width_set(2)
    # gpu.state.point_size_set(5)
    batch.draw(shader)


class FACEIT_OT_DrawFaceitVertexGroup(bpy.types.Operator):
    ''' Register the main surface. Draws an overlay to help you select the right vertices.'''
    bl_idname = 'faceit.draw_faceit_vertex_group'
    bl_label = 'Draw Vertex Group'
    bl_options = {'UNDO', 'INTERNAL'}

    faceit_vertex_group_name: bpy.props.StringProperty(
        name='FaceitGroup',
        default='',
        options={'SKIP_SAVE'}
    )

    def __init__(self):
        self._handler = None
        self._blf_handler = None
        self.dg = None
        self.vert_data = None
        self.indices = None
        self.bm = None

    @classmethod
    def poll(cls, context):
        return (context.mode in ('OBJECT', 'EDIT_MESH'))  # 'EDIT_MESH'

    @classmethod
    def description(self, context, properties):
        _doc_string = "Works different in Edit / Object Mode.\n"
        if context.mode == 'EDIT_MESH':
            _doc_string += "Edit Mode: Assign selected vertices to this group.\n"
        else:
            _doc_string += "Object Mode: Assign all vertices of the selected object to this group.\n"
        _doc_string += "You can assign multiple groups to one object.\n\n"
        _doc_string += "The main group: (face, skull, body, skin)\n"
        _doc_string += "This group should consist of one connected surface. In other words, all vertices assigned to this group should be linked by edges. It does not matter if this encompasses the skull or even the whole body. \n"
        _doc_string += "Read more in the Faceit documentation."
        return _doc_string

    def get_vertex_data(self, bm):
        ''' Get the relevant vertex data for the shader.'''
        # self.mat @
        self.vert_data = np.array([v.co for v in bm.verts], np.float32)
        self.indices = np.array([(e.verts[0].index, e.verts[1].index) for e in bm.edges], np.int32)
        # self.indices = [[loop.vert.index for loop in looptris]
        #                 for looptris in bm.calc_loop_triangles()]

    def delete_vertices_outside(self, bm, vids):
        '''Deletes all vertices that are not in the island_ids'''
        verts_delete = [v for v in bm.verts if v.index not in vids]
        if verts_delete:
            bmesh.ops.delete(bm, geom=verts_delete, context='VERTS')

    def modal(self, context, event):
        context.area.tag_redraw()
        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
            # bpy.types.SpaceView3D.draw_handler_remove(self._blf_handler, 'WINDOW')
            self.bm.free()
            # self.report({'INFO'}, "Cancelled.")
            context.scene.faceit_vertex_groups[self.faceit_vertex_group_name].is_drawn = False
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        # activate simplify to avoid rendering high poly meshes
        simplify_state = context.scene.render.use_simplify
        simplify_count = context.scene.render.simplify_subdivision
        context.scene.render.use_simplify = True
        context.scene.render.simplify_subdivision = 0
        show_unassigned = 'UNASSIGNED' == self.faceit_vertex_group_name
        mode_save = futils.get_object_mode_from_context_mode(context.mode)
        grp_prop = context.scene.faceit_vertex_groups[self.faceit_vertex_group_name]
        is_masked = grp_prop.is_masked
        if is_masked:
            bpy.ops.faceit.mask_group('INVOKE_DEFAULT', vgroup_name=self.faceit_vertex_group_name, operation='REMOVE')
        if mode_save != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        if context.area.type == 'VIEW_3D':
            self.dg = context.evaluated_depsgraph_get()
            bm = bmesh.new()
            any_group_found = False
            # Get bmesh consisting of all vertices among
            # all objects that are in the group.
            for obj in futils.get_faceit_objects_list():
                if not show_unassigned:
                    vgroup = obj.vertex_groups.get(self.faceit_vertex_group_name)
                    if not vgroup:
                        continue
                    obj = obj.evaluated_get(self.dg)
                    vg_idx = vgroup.index
                    vids = [v.index for v in obj.data.vertices if vg_idx in [vg.group for vg in v.groups]]
                else:
                    obj = obj.evaluated_get(self.dg)
                    vids = set()
                    for vgroup in obj.vertex_groups:
                        if vgroup.name.startswith('faceit_'):
                            vg_idx = vgroup.index
                            vids.update([v.index for v in obj.data.vertices
                                         if vg_idx in [vg.group for vg in v.groups]])
                    # Get all vertices that are not in any group.
                    vids = [v.index for v in obj.data.vertices if v.index not in vids]
                if not vids:
                    continue
                any_group_found = True
                obj = obj.evaluated_get(self.dg)
                # if obj.mode == 'EDIT':
                #     ob_bm = bmesh.from_edit_mesh(obj.data)
                #     bm_temp = ob_bm.copy()
                #     bmesh.update_edit_mesh(obj.data)
                #     ob_bm.free()
                # else:
                bm_temp = bmesh.new()
                bm_temp.from_mesh(obj.data)
                # print('obj.data edges', len(obj.data.edges))
                # print('bm_temp edges', len(bm.edges))
                self.delete_vertices_outside(bm_temp, vids)
                me = bpy.data.meshes.new('temp_mesh')
                bm_temp.to_mesh(me)
                bm_temp.free()
                for v in me.vertices:
                    v.co = obj.matrix_world @ v.co
                bm.from_mesh(me)
                bpy.data.meshes.remove(me)

            if not any_group_found:
                if mode_save != 'OBJECT':
                    bpy.ops.object.mode_set(mode=mode_save)
                context.scene.render.use_simplify = simplify_state
                context.scene.render.simplify_subdivision = simplify_count
                self.report({'WARNING'}, f"No vertices assigned to group {self.faceit_vertex_group_name}")
                bm.free()
                return {'CANCELLED'}
            # Weird bug where the mesh is not updated.
            me = bpy.data.meshes.new('temp_mesh')
            bm.to_mesh(me)
            bpy.data.meshes.remove(me)
            # Get the relevant vertex data for the shader.
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            self.bm = bm
            self.get_vertex_data(bm)
            args = (self,)
            self._handler = bpy.types.SpaceView3D.draw_handler_add(draw_group_callback, args, 'WINDOW', 'POST_VIEW')
        else:
            if mode_save != 'OBJECT':
                bpy.ops.object.mode_set(mode=mode_save)
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        context.scene.render.use_simplify = simplify_state
        context.scene.render.simplify_subdivision = simplify_count
        if mode_save != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode_save)
        grp_prop.is_drawn = True
        if is_masked:
            bpy.ops.faceit.mask_group('INVOKE_DEFAULT', vgroup_name=self.faceit_vertex_group_name, operation='ADD')
        return {'RUNNING_MODAL'}


class FACEIT_OT_MaskMainObject(bpy.types.Operator):
    '''	Mask all geometry that is not assigned to the main face. '''
    bl_idname = 'faceit.mask_main'
    bl_label = 'Mask Main Face'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        main_obj = futils.get_main_faceit_object()
        main_group = main_obj.vertex_groups.get("faceit_main")
        if not main_group:
            self.report({'ERROR'}, "Couldn't find the faceit_main vertex group. Make sure to assign it in the setup tab.")
            return {'CANCELLED'}
        # add the mask modifier
        mod = main_obj.modifiers.get("Main Mask")
        if not mod:
            mod = main_obj.modifiers.new(type='MASK', name="Main Mask")
        mod.vertex_group = main_group.name
        mod.show_viewport = True
        # hide all other faceit objects
        faceit_objects = futils.get_faceit_objects_list()
        for obj in faceit_objects:
            if obj != main_obj:
                obj.hide_set(True)

        return {'FINISHED'}


class FACEIT_OT_MaskGroup(bpy.types.Operator):
    '''	Mask all vertices that are not assigned to the specified group. This only affects objects that are assigned to the group. '''
    bl_idname = 'faceit.mask_group'
    bl_label = 'Mask Faceit Vertex Group'
    bl_options = {'UNDO', 'INTERNAL'}

    vgroup_name: bpy.props.StringProperty(
        name="Vertex Group",
        description="Vertex Group to use for the mask",
        default="",
        options={'SKIP_SAVE'}
    )
    inverse: bpy.props.BoolProperty(
        name="Inverse",
        description="Invert the mask",
        default=True,
        options={'SKIP_SAVE'}
    )
    operation: bpy.props.EnumProperty(
        items=(
            ('ADD', 'Add', 'Add mask mods'),
            ('REMOVE', 'Remove', 'Remove mask mods'),
            ('INVERT', 'Invert', 'Invert mask mods'),
        ),
    )
    mask_all: bpy.props.BoolProperty()

    def __init__(self):
        self.grp_prop = None

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        faceit_objects = futils.get_faceit_objects_list()
        grps = vg_utils.get_vertex_groups_from_objects(faceit_objects)
        self.grp_prop = context.scene.faceit_vertex_groups.get(self.vgroup_name)
        if self.vgroup_name in grps:
            return self.execute(context)
        else:
            self.report({'WARNING'}, f"No vertices assigned to group {self.vgroup_name}")
            context.scene.faceit_vertex_groups[self.vgroup_name].is_masked = False
            return {'CANCELLED'}

    def execute(self, context):
        mode_save = futils.get_object_mode_from_context_mode(context.mode)
        if mode_save != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        faceit_objects = futils.get_faceit_objects_list()
        is_main = 'faceit_main' == self.vgroup_name
        if is_main:
            vgroup_mask_name = 'faceit_main_mask'
        else:
            vgroup_mask_name = self.vgroup_name

        mod_name = "Mask " + self.vgroup_name
        for obj in faceit_objects:
            if self.vgroup_name in obj.vertex_groups:
                mod = obj.modifiers.get(mod_name)
                if self.operation == 'REMOVE':
                    if mod:
                        obj.modifiers.remove(mod)
                    if is_main:
                        grp = obj.vertex_groups.get(vgroup_mask_name)
                        if grp:
                            obj.vertex_groups.remove(grp)
                        break
                elif self.operation == 'ADD':
                    # if it's the main group, create a temp vgroup that holds only vertices thare assigned to main group !only!
                    # Remove all verts from group that are assigned to other faceit groups.
                    if is_main:
                        vids = set([v.index for v in vg_utils.get_verts_in_vgroup(obj, self.vgroup_name)])
                        for grp in obj.vertex_groups:
                            if grp.name == self.vgroup_name:
                                continue
                            if grp.name.startswith("faceit_"):
                                vids -= set([v.index for v in vg_utils.get_verts_in_vgroup(obj, grp.name)])
                        if vids:
                            vg_utils.assign_vertex_grp(
                                obj,
                                list(vids),
                                vgroup_mask_name,
                                overwrite='REPLACE'
                            )
                    if mod is None:
                        mod = obj.modifiers.new(type='MASK', name=mod_name)
                    mod.vertex_group = vgroup_mask_name
                    mod.show_in_editmode = True
                    mod.show_on_cage = True
                    mod.invert_vertex_group = self.grp_prop.mask_inverted
                    mod.show_viewport = True
                elif self.operation == 'INVERT':
                    if mod:
                        mod.invert_vertex_group = not self.grp_prop.mask_inverted
        if mode_save != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode_save)

        if self.operation == 'ADD':
            self.grp_prop.is_masked = True
        elif self.operation == 'REMOVE':
            self.grp_prop.is_masked = False
            # self.grp_prop.mask_inverted = False
        elif self.operation == 'INVERT':
            self.grp_prop.mask_inverted = not self.grp_prop.mask_inverted
        return {'FINISHED'}


class FACEIT_OT_UnmaskMainObject(bpy.types.Operator):
    '''	Mask all geometry that is not assigned to the main face. '''
    bl_idname = 'faceit.unmask_main'
    bl_label = 'Remove Mask'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        main_obj = futils.get_main_faceit_object()
        main_group = None
        if main_obj:
            main_group = main_obj.vertex_groups.get("faceit_main")
        if not main_group:
            self.report({'WARNING'}, "Couldn't find the faceit_main vertex group. Make sure to assign it in the setup tab.")
            return {'CANCELLED'}
        # add the mask modifier
        mod = main_obj.modifiers.get("Main Mask")
        if mod:
            main_obj.modifiers.remove(mod)
        # mod.vertex_group = main_group

        # hide all other faceit objects
        faceit_objects = futils.get_faceit_objects_list()
        for obj in faceit_objects:
            if obj != main_obj:
                obj.hide_set(False)

        return {'FINISHED'}
