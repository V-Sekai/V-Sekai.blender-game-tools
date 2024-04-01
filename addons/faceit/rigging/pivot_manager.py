#
import bmesh
from bmesh.types import BMesh, BMVert
import bpy
import gpu
import blf
from mathutils import Matrix, Vector
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d

from ..core.vgroup_utils import get_vertex_groups_from_objects
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from ..landmarks import landmarks_data as lm_data
from . import rig_utils


def copy_pivot_from_bone(ref_rig, bone_name):
    '''Get the location of the pivot from the bone'''
    if ref_rig:
        eye_bone = ref_rig.data.bones.get(bone_name)
        if eye_bone:
            pos = ref_rig.matrix_world @ eye_bone.matrix_local.to_4x4().to_translation()
            return pos


def get_eye_pivot_from_landmarks(context):
    '''Get the location of the eye pivot from the landmarks'''
    # place based on landmark positions
    # Asymmetric Landmarks:
    # ...
    scene = context.scene
    landmarks_obj = scene.objects.get('facial_landmarks')
    pos = Vector((0, 0, 0))
    if landmarks_obj:
        mw = landmarks_obj.matrix_world
        if scene.faceit_asymmetric:
            pass
        else:
            # Symmetric Landmarks:
            # Left Eye (mirror Right Eye):
            # between vertex 19 and 27 on the z axis
            # move to vertex 25 on the y axis
            v1 = mw @ landmarks_obj.data.vertices[19].co
            v2 = mw @ landmarks_obj.data.vertices[27].co
            v3 = mw @ landmarks_obj.data.vertices[25].co
            pos = (v1 + v2) / 2
            pos.y = v3.y
    return pos


class PivotsClass:
    """Class to manage the eye pivot points in the viewport"""

    def __init__(self) -> None:
        self._handle = None
        self._handle_blf = None
        self.lm_obj = None
        self.pivot_left = Vector((0, 0, 0))
        self.pivot_right = Vector((0, 0, 0))
        self.manual_pivot_left = Vector((0, 0, 0))
        self.manual_pivot_right = Vector((0, 0, 0))
        self.area_3d = None
        self.is_drawing = False
        self.mode = 'AUTO'  # AUTO, MANUAL
        self.rv3d = None
        self.region = None
        self.selected_verts = []
        self.lm_pivot_vert_idx_left = 41
        self.lm_pivot_vert_idx_right = 73
        self.lm_default_vert_count = 41
        self._symmetric = True
        self.locator_scale = 0.2
        self.snap_toggled = False
        self.last_active_vertex: int = None
        self.jaw_pivot = Vector((0, 0, 0))
        self.draw_jaw_pivot = False

    @property
    def symmetric(self):
        return self._symmetric

    @symmetric.setter
    def symmetric(self, value):
        self._symmetric = value
        if value:
            self.lm_pivot_vert_idx_left = 41
            self.lm_default_vert_count = 41
        else:
            self.lm_pivot_vert_idx_left = 72
            self.lm_default_vert_count = 73

    def initialize_pivots(self, context):
        '''Initialize the pivot points when loading a new scene.'''
        self.load_saved_pivots(context)
        self.symmetric = not context.scene.faceit_asymmetric
        if self.mode == 'AUTO':
            vgroups = get_vertex_groups_from_objects()
            if self.pivot_left == Vector((0, 0, 0)):
                if not context.scene.faceit_eye_pivot_group_L:
                    if 'faceit_left_eyeball' in vgroups:
                        context.scene.faceit_eye_pivot_group_L = 'faceit_left_eyeball'
                    elif 'faceit_left_eyes_other' in vgroups:
                        context.scene.faceit_eye_pivot_group_L = 'faceit_left_eyes_other'
            if self.pivot_right == Vector((0, 0, 0)):
                if not context.scene.faceit_eye_pivot_group_R:
                    if 'faceit_right_eyeball' in vgroups:
                        context.scene.faceit_eye_pivot_group_R = 'faceit_right_eyeball'
                    elif 'faceit_right_eyes_other' in vgroups:
                        context.scene.faceit_eye_pivot_group_R = 'faceit_right_eyes_other'
        # initialize the pivot locator scale based on landmarks size
        lm_obj = context.scene.objects.get('facial_landmarks')
        if lm_obj:
            self.locator_scale = lm_obj.dimensions.x / 20
        if self.pivot_left == Vector((0, 0, 0)):
            pivot_left = context.scene.faceit_eye_pivot_point_L = get_eye_pivot_from_landmarks(context)
            context.scene.faceit_eye_pivot_point_R = Vector((-pivot_left[0], pivot_left[1], pivot_left[2]))
            return False

        if context.scene.faceit_use_jaw_pivot:
            jaw_pivot_object = context.scene.objects.get('Jaw Pivot')
            if jaw_pivot_object:
                self.jaw_pivot = jaw_pivot_object.location
        return True

    def reset_pivots(self, context):
        self.pivot_left = self.pivot_right = self.manual_pivot_left = self.manual_pivot_right = context.scene.faceit_eye_manual_pivot_point_L = context.scene.faceit_eye_manual_pivot_point_R = context.scene.faceit_eye_pivot_point_L = context.scene.faceit_eye_pivot_point_R = Vector()
        context.scene.faceit_eye_pivot_placement = 'AUTO'

    def save_pivots(self, context):
        '''Save the manual pivot points to the scene'''
        context.scene.faceit_eye_manual_pivot_point_L = self.manual_pivot_left
        context.scene.faceit_eye_manual_pivot_point_R = self.manual_pivot_right

    def load_saved_pivots(self, context):
        '''Load the manual pivot points from the scene'''
        self.mode = context.scene.faceit_eye_pivot_placement
        self.pivot_left = context.scene.faceit_eye_pivot_point_L
        self.pivot_right = context.scene.faceit_eye_pivot_point_R
        self.manual_pivot_left = context.scene.faceit_eye_manual_pivot_point_L
        self.manual_pivot_right = context.scene.faceit_eye_manual_pivot_point_R

    def _save_manual_pivot(self):
        self.manual_pivot_left = self.pivot_left
        self.manual_pivot_right = self.pivot_right

    def _restore_manual_pivot(self):
        if self.manual_pivot_left != Vector((0, 0, 0)):
            self.pivot_left = self.manual_pivot_left
        if self.manual_pivot_right != Vector((0, 0, 0)):
            self.pivot_right = self.manual_pivot_right

    def change_mode(self, new_mode):
        if new_mode == self.mode:
            return
        elif new_mode == 'AUTO' and self.mode == 'MANUAL':
            self._save_manual_pivot()
        elif new_mode == 'MANUAL' and self.mode == 'AUTO':
            self._restore_manual_pivot()
        self.mode = new_mode

    def __del__(self):
        self.remove_handle()
        self.remove_blf_hanlde()
        self.lm_obj = None

    def cancel(self):
        self.remove_handle()
        self.remove_blf_hanlde()
        self.lm_obj = None

    def get_3d_area(self, context):
        if context.area is not None:
            if context.area.type == 'VIEW_3D':
                return context.area
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                return area
        return None

    def get_region_data_from_area(self, area):
        region = None
        for r in area.regions:
            if r.type == 'WINDOW':
                region = r
        rv3d = area.spaces.active.region_3d
        return region, rv3d

    def is_valid(self, lm_obj):
        if lm_obj is None:
            return False
        elif lm_obj["state"] < 4:
            return False
        elif (lm_obj.hide_viewport or lm_obj.hide_get()):
            return False
        return True

    def get_pivot_points(self, context, lm_obj):
        jaw_pivot_obj = context.scene.objects.get('Jaw Pivot')
        if jaw_pivot_obj:
            self.draw_jaw_pivot = True
            context.scene.faceit_jaw_pivot = self.jaw_pivot = jaw_pivot_obj.location
        else:
            self.draw_jaw_pivot = False
        if context.scene.faceit_eye_pivot_placement == 'MANUAL':
            if lm_obj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(lm_obj.data)
                bm.verts.ensure_lookup_table()
                self.pivot_left = lm_obj.matrix_world @ bm.verts[self.lm_pivot_vert_idx_left].co
                if self.symmetric:
                    self.pivot_right = Vector((-self.pivot_left[0], self.pivot_left[1], self.pivot_left[2]))
                else:
                    self.pivot_right = lm_obj.matrix_world @ bm.verts[self.lm_pivot_vert_idx_right].co
                self.selected_verts = self.get_selected_vert_indices(bm)
                if context.scene.faceit_pivot_vertex_auto_snap:
                    active_vert = self.get_active_vert_index(bm)
                    if active_vert != self.last_active_vertex:
                        self.last_active_vertex = active_vert
                        if active_vert == self.lm_pivot_vert_idx_left:
                            context.scene.tool_settings.use_snap = False
                            self.snap_toggled = True
                        elif self.snap_toggled:
                            context.scene.tool_settings.use_snap = True
                            self.snap_toggled = False
                bmesh.update_edit_mesh(lm_obj.data)
        else:
            self.pivot_left = context.scene.faceit_eye_pivot_point_L
            self.pivot_right = context.scene.faceit_eye_pivot_point_R

    def get_selected_vert_indices(self, bm: BMesh):
        '''Returns a list of indices of selected vertices'''
        return [v.index for v in bm.verts if v.select]

    def get_active_vert_index(self, bm: BMesh):
        '''Returns the index of the active vertex'''
        elem = bm.select_history.active
        if isinstance(elem, BMVert):
            return elem.index

    def draw_line(self, shader, origin, direction, scale):
        '''Draw a line from a given origin in a given direction'''
        end = (origin + direction * scale)
        # Create the batch for the shader and return it
        return batch_for_shader(shader, 'LINES', {"pos": [origin, end]}, indices=((0, 1),))

    def draw_callback(self, context):
        '''Draws a cross at the empty object's location'''
        if not context.scene.faceit_draw_pivot_locators:
            return
        self.lm_obj = context.scene.objects.get('facial_landmarks')
        if not self.is_valid(self.lm_obj):
            # self.cancel() can't remove draw_handles from here -> crashes blender
            return
        self.get_pivot_points(context, self.lm_obj)
        # Start the shader
        shader_name = 'UNIFORM_COLOR' if bpy.app.version[0] >= 4 else '3D_UNIFORM_COLOR'
        shader = gpu.shader.from_builtin(shader_name)
        shader.bind()
        shader.uniform_float("color", (0.0, 1, 0.0, 1.0))
        # Define directions
        directions = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((-1, 0, 0)),
            Vector((0, -1, 0)),
            Vector((0, 0, -1))]
        # scale of the lines
        batches = []
        pivots = [self.pivot_left, self.pivot_right]
        if self.draw_jaw_pivot:
            pivots.append(self.jaw_pivot)
        # Draw lines for the left and right pivot
        for pivot in pivots:
            mat = Matrix.Translation(pivot)
            origin = mat @ Vector((0, 0, 0))  # Convert coordinates in world space
            for direction in directions:
                batches.append(self.draw_line(shader, origin, direction, self.locator_scale))
        # Draw all the batches
        for batch in batches:
            batch.draw(shader)
        try:
            if self.mode == 'MANUAL':
                self._save_manual_pivot()
                self.save_pivots(context)
        except Exception as e:
            print(e)
            pass

    def draw_callback_blf(self, context, region, rv3d):
        ''' Write the name of each pivot in the view port.'''
        if not context.scene.faceit_draw_pivot_locators:
            return
        lm_obj = self.lm_obj
        if not self.is_valid(lm_obj):
            # self.cancel()
            return
        font_id = 0
        font_offset = 10
        select_color = (1, 1, 1, 1)
        deselect_color = (0.0, 0.0, 0.0, 1)
        blf.size(font_id, 20)
        # if left_pivot_selected:
        x, y = location_3d_to_region_2d(region, rv3d, self.pivot_left)
        draw_selected = self.mode == 'AUTO' or context.mode == 'OBJECT'
        draw_left_selected = draw_selected or self.lm_pivot_vert_idx_left in self.selected_verts
        if draw_left_selected:
            blf.color(font_id, *select_color)
        else:
            blf.color(font_id, *deselect_color)
        blf.position(font_id, x + font_offset, y - font_offset * 2, 0)
        blf.draw(font_id, 'Left Pivot')
        if draw_selected or self.lm_pivot_vert_idx_right in self.selected_verts or self.symmetric and draw_left_selected:
            blf.color(font_id, *select_color)
        else:
            blf.color(font_id, *deselect_color)
        x, y = location_3d_to_region_2d(region, rv3d, self.pivot_right)
        blf.position(font_id, x + font_offset, y - font_offset * 2, 0)
        blf.draw(font_id, 'Right Pivot')
        if self.draw_jaw_pivot:
            blf.color(font_id, *select_color)
            x, y = location_3d_to_region_2d(region, rv3d, self.jaw_pivot)
            blf.position(font_id, x + font_offset, y - font_offset * 2, 0)
            blf.draw(font_id, 'Jaw Pivot')

    def remove_handle(self):
        if self._handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except Exception as e:
                print('error removing handle')
                print(e)
            self._handle = None
        self.is_drawing = False

    def add_handle(self, context, initialize_pivots=True):
        if self._handle is None:
            if initialize_pivots:
                self.initialize_pivots(context)
            area_3d = self.get_3d_area(context)
            if area_3d is not None:
                self.area_3d = area_3d
                self._handle = bpy.types.SpaceView3D.draw_handler_add(
                    self.draw_callback, ((context,)), 'WINDOW', 'POST_VIEW')
                self.is_drawing = True
            else:
                self.is_drawing = False

    def remove_blf_hanlde(self):
        if self._handle_blf is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle_blf, 'WINDOW')
            except Exception as e:
                print('error removing handle')
                print(e)
            self._handle_blf = None

    def add_blf_handle(self, context):
        if self._handle_blf is None:
            if self.area_3d is None:
                self.area_3d = self.get_3d_area(context)
            if self.area_3d is not None:
                region, rv3d = self.get_region_data_from_area(self.area_3d)
                if region is not None and rv3d is not None:
                    self._handle_blf = bpy.types.SpaceView3D.draw_handler_add(
                        self.draw_callback_blf, ((context, region, rv3d)), 'WINDOW', 'POST_PIXEL')

    def get_eye_pivot_from_vertex_group(self, context, vgroup_name):
        '''Get the location of the eye pivot from the vertex group'''
        pos = Vector((0, 0, 0))
        objects = vg_utils.get_objects_with_vertex_group(vgroup_name, get_all=True)
        # get the evaluated objects
        if context is None:
            context = bpy.context
        objects = [o.evaluated_get(context.evaluated_depsgraph_get()) for o in objects]
        # Get the global vertex positions of all verts in vgroup in all objects
        global_vs = []
        for obj in objects:
            obj_vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            global_vs.extend([obj.matrix_world @ v.co for v in obj_vs])
        bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
        pos = rig_utils.get_median_pos(bounds)
        return pos

    def start_drawing(self, context, initialize=True):
        print('start drawing')
        if not self.is_drawing:
            self.add_handle(context, initialize_pivots=initialize)
            self.add_blf_handle(context)

    def stop_drawing(self):
        print('stop drawing')
        self.remove_handle()
        self.remove_blf_hanlde()

    def get_is_drawing(self):
        return self.is_drawing


if "PivotManager" not in globals():
    PivotManager: PivotsClass = PivotsClass()


def unregister():
    if "PivotManager" in globals():
        # global PivotManager
        PivotManager.cancel()
        # del PivotManager


class FACEIT_OT_AddManualPivotVertex(bpy.types.Operator):
    '''Add a vertex for editing the manual pivot point'''
    bl_idname = 'faceit.add_manual_pivot_vertex'
    bl_label = 'Add Manual Pivot Vertex'
    bl_options = {'UNDO'}

    pivot_position: bpy.props.FloatVectorProperty(
        name='Pivot Position',
        default=(0, 0, 0),
        subtype='XYZ',
        size=3,
        description='Position of the pivot point'
    )
    select_vertex: bpy.props.BoolProperty(
        name='Select Vertex',
        default=True,
        description='Select the vertex after adding it'
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        '''Adds a vertex to the mesh for manually setting the pivot point (EDIT MODE ONLY)'''
        PivotManager.change_mode(new_mode='MANUAL')
        lm_obj = context.scene.objects.get('facial_landmarks')
        if lm_obj is None:
            return {'CANCELLED'}
        if lm_obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(lm_obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(lm_obj.data)
        bm.verts.ensure_lookup_table()
        # check vertex count
        if self.select_vertex:
            for v in bm.verts:
                v.select = False
            bm.verts.ensure_lookup_table()
            bm.select_flush(True)
            bm.select_flush(False)

        pos = lm_obj.matrix_world.inverted() @ PivotManager.pivot_left
        pivots_already_created = len(bm.verts) > PivotManager.lm_default_vert_count
        pivot_verts = []
        if pivots_already_created:
            # the extra vertex already exists, just update its position
            v_piv = bm.verts[PivotManager.lm_pivot_vert_idx_left]
            v_piv.co = pos
        else:
            v_piv = bm.verts.new(pos)
        pivot_verts.append(v_piv)
        if not PivotManager.symmetric:
            pos = lm_obj.matrix_world.inverted() @ PivotManager.pivot_right
            if pivots_already_created:
                # the extra vertex already exists, just update its position
                v_piv = bm.verts[PivotManager.lm_pivot_vert_idx_right]
                v_piv.co = pos
            else:
                v_piv = bm.verts.new(pos)
            pivot_verts.append(v_piv)
        if self.select_vertex:
            for v_piv in pivot_verts:
                v_piv.select = True
                bm.select_history.add(v_piv)
        bm.verts.ensure_lookup_table()
        if lm_obj.mode == 'EDIT':
            bmesh.update_edit_mesh(lm_obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
        else:
            bm.to_mesh(lm_obj.data)
            bm.free()
            if lm_obj == context.active_object:
                bpy.ops.object.mode_set(mode='EDIT')
        context.scene.faceit_eye_pivot_placement = 'MANUAL'
        PivotManager.start_drawing(context)
        context.scene.faceit_draw_pivot_locators = True
        return {'FINISHED'}


class FACEIT_OT_RemoveManualPivotVertex(bpy.types.Operator):
    '''Remove the vertex for editing the manual pivot point'''
    bl_idname = 'faceit.remove_manual_pivot_vertex'
    bl_label = 'Remove Manual Pivot Vertex'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        PivotManager.change_mode(new_mode='AUTO')
        lm_obj = context.scene.objects.get('facial_landmarks')
        if lm_obj is None:
            return {'CANCELLED'}
        if lm_obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(lm_obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(lm_obj.data)
        bm.verts.ensure_lookup_table()
        # check vertex count
        if len(bm.verts) > PivotManager.lm_default_vert_count:
            bm.verts.remove(bm.verts[-1])
            bm.verts.ensure_lookup_table()
            if not PivotManager.symmetric:
                bm.verts.remove(bm.verts[-1])
                bm.verts.ensure_lookup_table()
        if lm_obj.mode == 'EDIT':
            bmesh.update_edit_mesh(lm_obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
        else:
            bm.to_mesh(lm_obj.data)
            bm.free()
        context.scene.faceit_eye_pivot_placement = 'AUTO'
        PivotManager.start_drawing(context)
        return {'FINISHED'}


class FACEIT_OT_ResetManualPivots(bpy.types.Operator):
    '''Reset the manual eye pivots'''
    bl_idname = 'faceit.reset_manual_pivots'
    bl_label = 'Reset Manual Pivots'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        lm_obj = context.scene.objects.get('facial_landmarks')
        if lm_obj is not None:
            return lm_obj.mode == 'EDIT'

    def execute(self, context):
        lm_obj = context.scene.objects.get('facial_landmarks')
        if context.mode == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(lm_obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(lm_obj.data)
        bm.verts.ensure_lookup_table()
        # check vertex count
        if len(bm.verts) > PivotManager.lm_default_vert_count:
            if PivotManager.lm_pivot_vert_idx_left in PivotManager.selected_verts:
                v = bm.verts[PivotManager.lm_pivot_vert_idx_left]
                pivot = lm_obj.matrix_world.inverted() @ context.scene.faceit_eye_pivot_point_L
                v.co = pivot
            if not PivotManager.symmetric:
                if PivotManager.lm_pivot_vert_idx_right in PivotManager.selected_verts:
                    v = bm.verts[PivotManager.lm_pivot_vert_idx_right]
                    pivot = lm_obj.matrix_world.inverted() @ context.scene.faceit_eye_pivot_point_R
                    v.co = pivot
        bm.verts.ensure_lookup_table()
        if context.mode == 'EDIT_MESH':
            bmesh.update_edit_mesh(lm_obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
        else:
            bm.to_mesh(lm_obj.data)
            bm.free()
        PivotManager.start_drawing(context)
        return {'FINISHED'}


class FACEIT_OT_AddJawPivotEmpty(bpy.types.Operator):
    bl_idname = 'faceit.add_jaw_pivot_empty'
    bl_label = 'Add Jaw Pivot Empty'
    bl_options = {'UNDO'}

    select_object: bpy.props.BoolProperty(
        name='Select Object',
        default=True,
        description='Select the Object after creating it'
    )
    restore_saved_pivot: bpy.props.BoolProperty(
        name='Restore Saved Pivot',
        default=False,
        description='Restore the saved pivot position',
        options={'SKIP_SAVE'}
    )

    pivot_name = "Jaw Pivot"

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        if context.scene.faceit_jaw_pivot != Vector((0, 0, 0)):
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'restore_saved_pivot')

    def execute(self, context):
        '''Adds a vertex to the mesh for manually setting the pivot point (EDIT MODE ONLY)'''
        scene = context.scene
        snap_settings = scene.tool_settings.use_snap
        scene.tool_settings.use_snap = False

        lm_obj = futils.get_object('facial_landmarks')
        faceit_collection = futils.get_faceit_collection(force_access=True, create=True)
        if not faceit_collection:
            self.report({'ERROR'}, "Faceit Collection not found.")
            return {'CANCELLED'}
        if lm_obj is None:
            self.report({'ERROR'}, "Facial Landmarks object not found.")
            return {'CANCELLED'}
        if context.object:
            bpy.ops.object.mode_set(mode='OBJECT')
            futils.clear_object_selection()

        _lm_size = lm_obj.dimensions.x / 8
        pos = Vector((0, 0, 0))
        if self.restore_saved_pivot:
            pos = context.scene.faceit_jaw_pivot
        else:
            if scene.faceit_asymmetric:
                pos_1 = lm_obj.matrix_world @ lm_obj.data.vertices[24].co
                pos_2 = lm_obj.matrix_world @ lm_obj.data.vertices[25].co
                pos = (pos_1 + pos_2) / 2
            else:
                pos = lm_obj.matrix_world @ lm_obj.data.vertices[22].co
                pos.x = 0

        obj = bpy.data.objects.get(self.pivot_name)
        if not obj:
            obj = bpy.data.objects.new(self.pivot_name, None)
            obj.empty_display_type = 'SPHERE'
            faceit_collection.objects.link(obj)
            obj.empty_display_size = _lm_size
            obj.show_name = False
            obj.select_set(state=True)
            obj.show_in_front = True
            if not context.scene.faceit_asymmetric:
                obj.lock_location[0] = True
        obj.location = pos
        PivotManager.start_drawing(context)
        scene.tool_settings.use_snap = snap_settings
        return {'FINISHED'}


class FACEIT_OT_RemoveJawPivotEmpty(bpy.types.Operator):
    bl_idname = 'faceit.remove_jaw_pivot_empty'
    bl_label = 'Remove Jaw Pivot Empty'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        jaw_pivot_object = context.scene.objects.get('Jaw Pivot')
        if not jaw_pivot_object:
            self.report({'ERROR'}, "Jaw Pivot object not found.")
            return {'CANCELLED'}
        bpy.data.objects.remove(jaw_pivot_object)
        context.scene.faceit_use_jaw_pivot = False
        return {'FINISHED'}


class FACEIT_OT_ResetJawPivotEmpty(bpy.types.Operator):
    bl_idname = 'faceit.reset_jaw_pivot_empty'
    bl_label = 'Reset Jaw Pivot Empty'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        jaw_pivot_object = context.scene.objects.get('Jaw Pivot')
        if not jaw_pivot_object:
            self.report({'ERROR'}, "Jaw Pivot object not found.")
            return {'CANCELLED'}
        lm_obj = context.scene.objects.get('facial_landmarks')
        if not lm_obj:
            self.report({'ERROR'}, "Facial Landmarks object not found.")
            return {'CANCELLED'}
        pos = Vector((0, 0, 0))

        pos = Vector((0, 0, 0))
        if lm_obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(lm_obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(lm_obj.data)
        bm.verts.ensure_lookup_table()
        if context.scene.faceit_asymmetric:
            pos_1 = lm_obj.matrix_world @ bm.verts[24].co
            pos_2 = lm_obj.matrix_world @ bm.verts[25].co
            pos = (pos_1 + pos_2) / 2
        else:
            pos = lm_obj.matrix_world @ bm.verts[22].co
            pos.x = 0
        if lm_obj.mode == 'EDIT':
            bmesh.update_edit_mesh(lm_obj.data)
        else:
            bm.free()
        PivotManager.jaw_pivot = pos
        jaw_pivot_object.location = pos
        PivotManager.start_drawing(context)
        return {'FINISHED'}


def create_empty(name, size=1.0):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = size
    obj.show_name = True
    obj.show_in_front = True
    obj.lock_rotation[0] = True
    obj.lock_rotation[1] = True
    obj.lock_rotation[2] = True
    return obj


def get_teeth_locator_positions(target='upper'):
    """Get the location of the teeth locators
    target: 'upper','lower'
    """
    scene = bpy.context.scene
    if scene.faceit_teeth_pivot_options == 'GEO':
        vgroup_name = scene.faceit_teeth_pivot_group_u if target == 'upper' else scene.faceit_teeth_pivot_group_l
        pos = Vector((0, 0, 0))
        objects = vg_utils.get_objects_with_vertex_group(vgroup_name, get_all=True)
        # Get the global vertex positions of all verts in vgroup in all objects
        global_vs = []
        for obj in objects:
            obj_vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
            global_vs.extend([obj.matrix_world @ v.co for v in obj_vs])
        bounds = rig_utils.get_bounds_from_locations(global_vs, 'y')
        pos = rig_utils.get_median_pos(bounds)
        if scene.faceit_asymmetric:
            bounds = rig_utils.get_bounds_from_locations(global_vs, 'x')
            pos.x = rig_utils.get_median_pos(bounds).x
        else:
            pos.x = 0
        return pos
    elif scene.faceit_teeth_pivot_options == 'MANUAL':
        # place based on landmark positions
        # Symmetric Landmarks:
        # Upper Teeth:
        # z axis: vertex 8
        # y axis: vertex 15
        # x axis: 0
        # Lower Teeth:
        # z axis: vertex 5
        # y axis: vertex 15
        # x axis: 0
        # Asymmetric Landmarks:
        # ...
        pass


def update_eye_locator_position(mirror=False):
    left_pos = get_eye_locator_positions('left')
    right_pos = get_eye_locator_positions('right')
    if mirror:
        if left_pos and not right_pos:
            right_pos = left_pos.copy()
            right_pos.x *= -1
        if right_pos and not left_pos:
            left_pos = right_pos.copy()
            left_pos.x *= -1
    return left_pos, right_pos


def update_teeth_locator_position():
    upper_pos = get_teeth_locator_positions('upper')
    lower_pos = get_teeth_locator_positions('lower')
    return upper_pos, lower_pos


def get_locator_names(target_locators='ALL'):
    """Get the eye locator empties
    target_locators: string in ('ALL','EYE','TEETH','JAW')
    """
    if target_locators == 'ALL':
        locator_names = lm_data.LOCATOR_NAMES
    elif target_locators == 'EYE':
        locator_names = lm_data.LOCATOR_NAMES[:2]
    elif target_locators == 'TEETH':
        locator_names = lm_data.LOCATOR_NAMES[2:4]
    else:
        locator_names = lm_data.LOCATOR_NAMES[4:]
    return locator_names


def get_locator_empties(target_locators='ALL', create=True):
    """Get the eye locator empties
    target_locators: string in ('ALL','EYE','TEETH','JAW')
    """
    locator_names = get_locator_names(target_locators)
    lm_obj = futils.get_object('facial_landmarks')
    if create:
        if lm_obj:
            _lm_size = lm_obj.dimensions.x / 8
        else:
            _lm_size = 0.01
    locators = []
    for name in locator_names:
        loc_empty = bpy.data.objects.get(name)
        if loc_empty:
            if loc_empty.name not in bpy.context.scene.objects:
                bpy.data.objects.remove(loc_empty)
                loc_empty = None
        if not loc_empty and create:
            faceit_collection = futils.get_faceit_collection(force_access=True, create=True)
            loc_empty = create_empty(name, _lm_size)
            faceit_collection.objects.link(loc_empty)
        if loc_empty:
            locators.append(loc_empty)
            # check if the locator object is animated
            if loc_empty.animation_data:
                loc_empty.animation_data_clear()
    return locators


def set_locator_hidden_state(target_locators='ALL', hide=True):
    locators = get_locator_empties(target_locators, create=False)
    for obj in locators:
        futils.set_hide_obj(obj, hide)
