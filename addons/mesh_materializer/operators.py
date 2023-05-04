import bpy
import bmesh
from . import utils
from . utils import MeshMaterializer
import mathutils
from mathutils import Vector
from bpy_extras import view3d_utils
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view
from . import ui
from . import props
from . props import MeshMaterializerSourceObject, MeshMaterializerGeneralProperty, MeshMaterializerCustomProperty

class MeshMaterializerAddSceneObj_OT_Operator(bpy.types.Operator):
    """Add a selected source object to the scene properties"""
    bl_idname = "view3d.mesh_materializer_add_scene_object"
    bl_label = "Mesh Materializer - add scene object"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        if context.scene.mesh_mat_object_to_add is None:
            self.report({'ERROR'}, 'No object to add.')
            return {'CANCELLED'}
            
        new_prop = context.scene.mesh_mat_source_objects.add()
        new_prop.name = context.scene.mesh_mat_object_to_add.name
        context.scene.mesh_mat_object_to_add = None
        props.exec_interactive(self, context)
        return {'FINISHED'}

class MeshMaterializerAddSceneCollection_OT_Operator(bpy.types.Operator):
    """Add a selected source object collection to the scene properties"""
    bl_idname = "view3d.mesh_materializer_add_scene_collection"
    bl_label = "Mesh Materializer - add scene collection"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        if context.scene.mesh_mat_collection_to_add is None:
            self.report({'ERROR'}, 'No object to add.')
            return {'CANCELLED'}
        new_col_prop = context.scene.mesh_mat_source_collections.add()
        new_col_prop.name = context.scene.mesh_mat_collection_to_add.name
        #also add the source objects...
        if bpy.data.collections.get(new_col_prop.name) is not None:
            for obj in bpy.data.collections.get(new_col_prop.name).all_objects:
                if obj.type == 'MESH':
                    new_prop = new_col_prop.source_objects.add()
                    new_prop.name = obj.name
                
        context.scene.mesh_mat_collection_to_add = None
        props.exec_interactive(self, context)
        return {'FINISHED'}

class MeshMaterializerRemoveSceneObj_OT_Operator(bpy.types.Operator):
    """Remove a selected source object to the scene properties"""
    bl_idname = "view3d.mesh_materializer_remove_scene_object"
    bl_label = "Mesh Materializer - remove scene object"
    bl_options = {"INTERNAL"}

    id_to_remove : bpy.props.IntProperty()

    def execute(self, context):

        new_prop = context.scene.mesh_mat_source_objects.remove(self.id_to_remove)
        props.exec_interactive(self, context)
        return {'FINISHED'}

class MeshMaterializerRemoveSceneObjFromCol_OT_Operator(bpy.types.Operator):
    """Remove a selected source object to a collection properties"""
    bl_idname = "view3d.mesh_materializer_remove_scene_object_col"
    bl_label = "Mesh Materializer - remove scene object from collection"
    bl_options = {"INTERNAL"}

    col_id : bpy.props.IntProperty()
    id_to_remove : bpy.props.IntProperty()

    def execute(self, context):
        col_prop = context.scene.mesh_mat_source_collections[self.col_id]
        new_prop = col_prop.source_objects.remove(self.id_to_remove)
        props.exec_interactive(self, context)
        return {'FINISHED'}

class MeshMaterializerRemoveCollectionObj_OT_Operator(bpy.types.Operator):
    """Remove a selected source collection to the scene properties"""
    bl_idname = "view3d.mesh_materializer_remove_scene_collection"
    bl_label = "Mesh Materializer - remove scene collection"
    bl_options = {"INTERNAL"}

    collection_to_remove : bpy.props.StringProperty(name='Collection to remove')

    def execute(self, context):
        id_to_remove = None
        for i in range(0, len(context.scene.mesh_mat_source_collections)):
            mesh_mat_source_collection = context.scene.mesh_mat_source_collections[i]
            if mesh_mat_source_collection.name == self.collection_to_remove:
                id_to_remove = i
                break

        new_prop = context.scene.mesh_mat_source_collections.remove(id_to_remove)
        props.exec_interactive(self, context)
        return {'FINISHED'}

# Delete selection
class MeshMaterializerDeleteSelection_OT_Operator(bpy.types.Operator):
    """Delete Geometry for Mesh Materializer"""
    bl_idname = "view3d.mesh_materializer_delete_selection"
    bl_label = "Mesh Materializer - Delete Selection"
    bl_options = {"INTERNAL", "REGISTER", "UNDO"}

    def execute(self, context):
        target_object = context.active_object

        if context.active_object.mode == 'EDIT':
            bm_target = bmesh.from_edit_mesh(target_object.data).copy()
            target_faces = [f for f in bm_target.faces if f.select]
        elif context.active_object.mode == 'OBJECT':
            bm_target = bmesh.new()
            bm_target.from_object(target_object, depsgraph=context.evaluated_depsgraph_get(), face_normals=True)
            target_faces = [f for f in bm_target.faces]

        if len(target_faces) > 0:
            ob_new, me_new, is_new_obj = utils.get_or_create_obj(context, target_object)

            utils.delete_mesh_material(context,
                                                bm_target,
                                                target_faces,
                                                me_new)

            me_new.update()

        
        if context.active_object.mode != 'EDIT':
            bm_target.free()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and \
            ((context.active_object.type == 'MESH' and \
            context.active_object.mode == 'OBJECT') or \
            (context.active_object.type == 'MESH' and \
            context.active_object.mode == 'EDIT' and \
            context.scene.tool_settings.mesh_select_mode[2])))


# dissolve geom
class MeshMaterializerDissolveGeom_OT_Operator(bpy.types.Operator):
    """Dissolve Cut Geometry for Mesh Materializer"""
    bl_idname = "view3d.mesh_materializer_dissolve_geom"
    bl_label = "Mesh Materializer - Dissolve Cuts"
    bl_options = {"INTERNAL", "REGISTER", "UNDO"}

    remove_doubles : bpy.props.BoolProperty(name="Merge by Distance", default=True)

    remove_doubles_cuts : bpy.props.BoolProperty(name="Cuts", default=True)

    remove_doubles_no_cuts : bpy.props.BoolProperty(name="Original Geometry", default=True)

    remove_doubles_amount_cuts : bpy.props.FloatProperty(
                                    name="Amount",
                                    description="Distance amount for removing doubles",
                                    default=0.0001,
                                    min=0,
                                    precision=4,
                                    step=0.01
                                    )

    remove_doubles_amount_no_cuts : bpy.props.FloatProperty(
                                    name="Amount",
                                    description="Distance amount for removing doubles",
                                    default=0.0001,
                                    min=0,
                                    precision=4,
                                    step=0.01
                                    )

    dissolve_edges : bpy.props.BoolProperty(name="Dissolve Edges", default=True)
    use_verts : bpy.props.BoolProperty(name="Use Verts", default=True)
    use_face_split_edge : bpy.props.BoolProperty(name="Use Face Split", default=False)
    dissolve_verts : bpy.props.BoolProperty(name="Dissolve Vertices", default=False)
    use_face_split_vert : bpy.props.BoolProperty(name="Use Face Split", default=True)
    use_boundary_tear : bpy.props.BoolProperty(name="Use Boundary Tear", default=False)
                                    
    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "remove_doubles")
        remove_doubles_amount_col = col.box()
        remove_doubles_amount_col.enabled = self.remove_doubles

        remove_doubles_amount_col.prop(self, "remove_doubles_cuts")
        remove_doubles_cuts_col = remove_doubles_amount_col.column()
        remove_doubles_cuts_col.enabled = self.remove_doubles_cuts
        remove_doubles_cuts_col.prop(self, "remove_doubles_amount_cuts")

        remove_doubles_amount_col.prop(self, "remove_doubles_no_cuts")
        remove_doubles_cuts_col = remove_doubles_amount_col.column()
        remove_doubles_cuts_col.enabled = self.remove_doubles_cuts
        remove_doubles_cuts_col.prop(self, "remove_doubles_amount_no_cuts")

        col.prop(self, "dissolve_edges")
        custom_col = col.box()
        custom_col.enabled = self.dissolve_edges
        custom_col.prop(self, "use_face_split_edge")
        custom_col.prop(self, "use_verts")
        
        col.prop(self, "dissolve_verts")
        custom_col = col.box()
        custom_col.enabled = self.dissolve_verts
        custom_col.prop(self, "use_face_split_vert")
        custom_col.prop(self, "use_boundary_tear")


    def execute(self, context):
        bm = bmesh.new()
        try:
            if context.active_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.from_mesh(context.active_object.data)

            if self.remove_doubles:
                utils.remove_doubles_for_cuts(bm, 
                                                self.remove_doubles_cuts,
                                                self.remove_doubles_amount_cuts,
                                                self.remove_doubles_no_cuts,
                                                self.remove_doubles_amount_no_cuts)

            utils.dissolve_cuts(context, 
                    bm, 
                    dissolve_edges=self.dissolve_edges, 
                    use_verts=self.use_verts, 
                    use_face_split_edge=self.use_face_split_edge,
                    dissolve_verts=self.dissolve_verts, 
                    use_face_split_vert=self.use_face_split_vert,
                    use_boundary_tear=self.use_boundary_tear)
            
            if context.active_object.mode == 'EDIT':
                bmesh.update_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.to_mesh(context.active_object.data)

        finally:
            if context.active_object.mode != 'EDIT':
                bm.free()
            context.active_object.data.update()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and \
            (context.active_object.type == 'MESH' and \
            context.active_object.mode in ['OBJECT', 'EDIT']))

# remove doubles
class MeshMaterializerRemoveDoubles_OT_Operator(bpy.types.Operator):
    """Remove Doubles for Mesh Materializer"""
    bl_idname = "view3d.mesh_materializer_remove_doubles"
    bl_label = "Mesh Materializer - Merge Vertices"
    bl_options = {"INTERNAL", "REGISTER", "UNDO"}

    remove_doubles : bpy.props.BoolProperty(name="Merge by Distance", default=True)

    remove_doubles_cuts : bpy.props.BoolProperty(name="Cuts", default=True)

    remove_doubles_no_cuts : bpy.props.BoolProperty(name="Source Geometry", default=True)

    remove_doubles_amount_cuts : bpy.props.FloatProperty(
                                    name="Amount",
                                    description="Distance amount for removing doubles",
                                    default=0.0001,
                                    min=0,
                                    precision=4,
                                    step=.01
                                    )

    remove_doubles_amount_no_cuts : bpy.props.FloatProperty(
                                    name="Amount",
                                    description="Distance amount for removing doubles",
                                    default=0.0001,
                                    min=0,
                                    precision=4,
                                    step=.01
                                    )
                                    
    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "remove_doubles")
        remove_doubles_amount_col = col.box()
        remove_doubles_amount_col.enabled = self.remove_doubles

        remove_doubles_amount_col.prop(self, "remove_doubles_cuts")
        remove_doubles_cuts_col = remove_doubles_amount_col.column()
        remove_doubles_cuts_col.enabled = self.remove_doubles_cuts
        remove_doubles_cuts_col.prop(self, "remove_doubles_amount_cuts")

        remove_doubles_amount_col.prop(self, "remove_doubles_no_cuts")
        remove_doubles_cuts_col = remove_doubles_amount_col.column()
        remove_doubles_cuts_col.enabled = self.remove_doubles_cuts
        remove_doubles_cuts_col.prop(self, "remove_doubles_amount_no_cuts")


    def execute(self, context):
        bm = bmesh.new()
        try:
            if context.active_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.from_mesh(context.active_object.data)

            if self.remove_doubles:
                utils.remove_doubles_for_cuts(bm, 
                                                self.remove_doubles_cuts,
                                                self.remove_doubles_amount_cuts,
                                                self.remove_doubles_no_cuts,
                                                self.remove_doubles_amount_no_cuts)

            
            if context.active_object.mode == 'EDIT':
                bmesh.update_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.to_mesh(context.active_object.data)

        finally:
            if context.active_object.mode != 'EDIT':
                bm.free()
            context.active_object.data.update()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and \
            (context.active_object.type == 'MESH' and \
            context.active_object.mode in ['OBJECT', 'EDIT']))


# Fill holes
class MeshMaterializerFillHoles_OT_Operator(bpy.types.Operator):
    """Fill Holes for Mesh Materializer"""
    bl_idname = "view3d.mesh_materializer_fill_holes"
    bl_label = "Mesh Materializer - Fill Holes"
    bl_options = {"INTERNAL", "REGISTER", "UNDO"}

    def execute(self, context):
        bm = bmesh.new()
        try:
            if context.active_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.from_mesh(context.active_object.data)

            utils.fill_holes(bm)
            
            if context.active_object.mode == 'EDIT':
                bmesh.update_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.to_mesh(context.active_object.data)

        finally:
            if context.active_object.mode != 'EDIT':
                bm.free()
            context.active_object.data.update()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and \
            (context.active_object.type == 'MESH' and \
            context.active_object.mode in ['OBJECT', 'EDIT']))


# Recalc Normals
class MeshMaterializerRecalcNormals_OT_Operator(bpy.types.Operator):
    """Recalculate Normals for Mesh Materializer"""
    bl_idname = "view3d.mesh_materializer_recalc_normals"
    bl_label = "Mesh Materializer - Recalculate Normals"
    bl_options = {"INTERNAL", "REGISTER", "UNDO"}

    def execute(self, context):
        bm = bmesh.new()
        try:
            if context.active_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.from_mesh(context.active_object.data)

            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            
            if context.active_object.mode == 'EDIT':
                bmesh.update_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.to_mesh(context.active_object.data)

        finally:
            if context.active_object.mode != 'EDIT':
                bm.free()
            context.active_object.data.update()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and \
            (context.active_object.type == 'MESH' and \
            context.active_object.mode in ['OBJECT', 'EDIT']))


# Remove Cut Objects Fill holes
class MeshMaterializerRemoveCutObjects_OT_Operator(bpy.types.Operator):
    """Remove Cut Objects for Mesh Materializer"""
    bl_idname = "view3d.mesh_materializer_remove_cut_objects"
    bl_label = "Mesh Materializer - Remove Cut Objects"
    bl_options = {"INTERNAL", "REGISTER", "UNDO"}

    def execute(self, context):
        bm = bmesh.new()
        try:
            if context.active_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.from_mesh(context.active_object.data)

            utils.remove_cut_objects(bm)
            
            if context.active_object.mode == 'EDIT':
                bmesh.update_edit_mesh(context.active_object.data)
            elif context.active_object.mode == 'OBJECT':
                bm.to_mesh(context.active_object.data)

        finally:
            if context.active_object.mode != 'EDIT':
                bm.free()
            context.active_object.data.update()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and \
            (context.active_object.type == 'MESH' and \
            context.active_object.mode in ['OBJECT', 'EDIT']))

class MeshMaterializerConfirm_OT_Operator(bpy.types.Operator):
    """Object may take some time to process"""
    bl_idname = "view3d.mesh_materializerconfirm"
    bl_label = "Higher poly count detected. Proceed?"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return main_tool_poll(context)

    def execute(self, context):
        bpy.ops.view3d.mesh_materializer('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class MeshMaterializer_OT_Operator(bpy.types.Operator):
    """Create Mesh Material from a selection (e.g. Object or Face)"""
    bl_idname = "view3d.mesh_materializer"
    bl_label = "Mesh Materializer"
    bl_description = "Creates a mesh around an object based on source objects and UV Mapping."
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        if (len(context.scene.mesh_mat_source_objects) == 0 and len(context.scene.mesh_mat_source_collections) == 0):
            self.report({'ERROR_INVALID_INPUT'}, 'No source objects selected for target object. Go to options in sidebar (N Key)')
            return {'CANCELLED'}

        if (len([sop for sop in context.scene.mesh_mat_source_objects if sop.is_enabled]) == 0) and \
            (len([sop for sop in context.scene.mesh_mat_source_collections if sop.is_enabled]) == 0):
            self.report({'ERROR_INVALID_INPUT'}, 'No enabled source objects selected for target object.')
            return {'CANCELLED'}

        if (len([sop for sop in context.scene.mesh_mat_source_objects if bpy.data.objects.get(sop.name) is None]) > 0) and \
            (len([sop for sop in context.scene.mesh_mat_source_collections if bpy.data.collections.get(sop.name) is None]) > 0):
            self.report({'ERROR_INVALID_INPUT'}, 'No existing source objects selected for target object.')
            return {'CANCELLED'}
        

        return self.execute(context)

    def cancel(self, context):
        self.bm_target.free()
        self.meshMaterializer.free()

    def execute(self, context):
        
        # Create property value objects.
        self.general_props, self.source_objects_props = invoke_props(context)
        self.meshMaterializer = MeshMaterializer(
                                    context,
                                    self.source_objects_props, 
                                    self.general_props
                                    )

        target_object = context.active_object

        msgs = validate_target_obj(target_object)
        if len(msgs) > 0:
            self.report({'ERROR_INVALID_INPUT'}, 'Invalid Target Object: ' + ','.join(msgs))
            return {'CANCELLED'}

        try:

            if context.active_object.mode == 'EDIT':
                self.bm_target = bmesh.from_edit_mesh(target_object.data).copy()
                target_faces = [f for f in self.bm_target.faces if f.select]
            elif context.active_object.mode == 'OBJECT':
                self.bm_target = bmesh.new()
                self.bm_target.from_object(target_object, depsgraph=context.evaluated_depsgraph_get(), face_normals=True)
                target_faces = [f for f in self.bm_target.faces]

            bpy.ops.ed.undo_push()
            self.meshMaterializer.generate_mesh_material(
                                            context,
                                            target_object,
                                            self.bm_target,
                                            target_faces,
                                            context.scene.mesh_mat_random_seed)
        finally:
            
            self.cancel(context)
                
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return main_tool_poll(context)
        

class MeshMaterializer_OT_ModalOperator(bpy.types.Operator):
    """Modal operator for interactive paining of mesh material."""
    bl_idname = "view3d.mesh_materializer_modal"
    bl_label = "Mesh Materializer Brush Tool"
    bl_options = {"INTERNAL", "REGISTER", "UNDO"}
    bl_description = "Creates a mesh around an object based on source objects and UV Mapping with a paintbrush style interaction."

    running_mesh_materializers = {}

    def validate_region(self):
        if not (MeshMaterializer_OT_ModalOperator.running_mesh_materializers.get(self._region) is self): return False
        return self.region_exists(self._region)

    def region_exists(self, r):
        wm = bpy.context.window_manager
        for window in wm.windows:
            for area in window.screen.areas:
                for region in area.regions:
                    if region == r: return True
        return False

    def find_faces(self, context, event):
        """Locate faces under the mouse and return their index information."""
        coord = (event.mouse_region_x, event.mouse_region_y)

        view_direction = view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, coord).normalized()    
        if self.rv3d.is_perspective:
           view_position = self.rv3d.view_matrix.inverted().translation
        else:
           view_position = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, coord, 100)

        view_direction_local = (self.rotation_euler_inverted @ view_direction).normalized()
        view_position_local = self.matrix_world_inv @ view_position

        location, normal, index, distance = self.bvhtree.ray_cast( view_position_local, view_direction_local)
        indexes = []
        if index is not None:
            results = self.bvhtree.find_nearest_range(location, context.scene.mesh_mat_brush_size)
            if len(results) > 0:
                for result in results:
                    #only check if we are facing the camera...
                    normal = result[1]
                    if normal.dot(view_direction_local) < 0:
                        indexes.append(result)

        return indexes

    def materialize_faces(self, context, meshMaterializer):
        """Add Mesh Material to active object."""
        if len(self.draw_faces) > 0:
            target_object = context.active_object
            meshMaterializer.generate_mesh_material(
                                            context,
                                            target_object,
                                            self.bm_target,
                                            self.faces,
                                            context.scene.mesh_mat_random_seed)

    def del_materialize_faces(self, context, meshMaterializer):
        """Delete Mesh Material from active object"""
        if len(self.draw_faces) > 0:
            target_object = context.active_object
            meshMaterializer.delete_mesh_material(
                                            context,
                                            target_object,
                                            self.bm_target,
                                            self.faces)

    def set_faces(self, context, event):
        """Set faces in operator as well as information for drawing."""
        self.draw_faces.clear()
        self.draw_verts.clear()
        self.draw_edges.clear()
        indexes = self.find_faces(context, event)
        if indexes is not None and len(indexes) > 0:

            # set actual faces.
            target_object = context.active_object
            self.bm_target.faces.ensure_lookup_table()
            for index in indexes:
                face = self.bm_target.faces[index[2]]
                self.faces.append(face)
            self.faces = list(set(self.faces))

            # set up for drawing functions.
            all_verts = []
            all_edges = []

            for face in self.faces:
                all_verts.extend(face.verts)
                all_edges.extend(face.edges)

            all_verts = list(set(all_verts))
            all_edges = list(set(all_edges))
            vert_index = 0
            vert_index_map = {}

            for vert in all_verts:
                vert_index_map[vert.index] = vert_index
                vert_index+=1

            edge_index = 0
            edge_index_map = {}
            for edge in all_edges:
                edge_index_map[edge.index] = edge_index
                edge_index+=1

            for face in self.faces:
                vert_indexes = []
                for vert in face.verts:
                    vert_indexes.append(vert_index_map[vert.index])
                edge_indexes = []
                for edge in face.edges:
                    edge_indexes.append(edge_index_map[edge.index])
                self.draw_faces[face.index] = {'vert_indexes' : vert_indexes, 'edge_indexes' : edge_indexes}

            for vert in all_verts:
                self.draw_verts[vert_index_map[vert.index]] = context.active_object.matrix_world @ vert.co.copy()

            for edge in all_edges:
                edge_verts = edge.verts
                self.draw_edges[edge_index_map[edge.index]] = [vert_index_map[edge.verts[0].index], vert_index_map[edge.verts[1].index]]

    def cancel(self, context):
        """Finish off and tidy."""
        self.bm_target.free()
        del self.bvhtree
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
        context.area.tag_redraw()
        context.region.tag_redraw()
        layer = context.view_layer
        layer.update()
        if MeshMaterializer_OT_ModalOperator.running_mesh_materializers.get(self._region) is self:
            del MeshMaterializer_OT_ModalOperator.running_mesh_materializers[self._region]
        context.scene.mesh_mat_toggle = False
        context.window.cursor_set("DEFAULT")
        self.is_cancelled = True

    def modal(self, context, event):
        """Handle modal operation."""

        if self.is_cancelled:
            return {'FINISHED'}

        if context.area:
            context.area.tag_redraw()

        if not self.validate_region() or not self.poll(context):
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'ESC' or context.scene.mesh_mat_toggle == False or \
            (context.active_object is None or context.active_object != self.target_object):
            self.cancel(context)
            return {'PASS_THROUGH'}

        if len(self.find_faces(context, event)) > 0:
            context.window.cursor_set("PAINT_BRUSH")


            self.general_props, self.source_objects_props = invoke_props(context)

            meshMaterializer = MeshMaterializer(
                                        context,
                                        self.source_objects_props, 
                                        self.general_props
                                        )

            if event.value == 'PRESS':
                self.is_drawing = True
                if event.type == 'LEFTMOUSE':
                    self.paint_mode = 'ADD'
                    return {'RUNNING_MODAL'}
                elif event.type == 'RIGHTMOUSE':
                    self.paint_mode = 'DEL'
                    return {'RUNNING_MODAL'}
            elif event.type =='MOUSEMOVE' and self.is_drawing:
                self.set_faces(context, event)
            elif event.value == 'RELEASE':
                self.is_drawing = False
                if self.paint_mode == 'DEL':
                    self.del_materialize_faces(context, meshMaterializer)
                elif self.paint_mode == 'ADD':
                    self.materialize_faces(context, meshMaterializer)
                self.clear_draw()
                return {'RUNNING_MODAL'}
            meshMaterializer.free()
        else:
            context.window.cursor_set("DEFAULT")

        return {'PASS_THROUGH'}

    def clear_draw(self):
        self.faces.clear()
        self.draw_faces.clear()
        self.draw_verts.clear()
        self.draw_edges.clear()

    def invoke(self, context, event):
        self.is_cancelled = False

        if (len(context.scene.mesh_mat_source_objects) == 0 and len(context.scene.mesh_mat_source_collections) == 0):
            self.report({'ERROR_INVALID_INPUT'}, 'No source objects selected for target object. Go to options in sidebar (N Key)')
            return {'CANCELLED'}

        if (len([sop for sop in context.scene.mesh_mat_source_objects if sop.is_enabled]) == 0) and \
            (len([sop for sop in context.scene.mesh_mat_source_collections if sop.is_enabled]) == 0):
            self.report({'ERROR_INVALID_INPUT'}, 'No enabled source objects selected for target object.')
            return {'CANCELLED'}

        if (len([sop for sop in context.scene.mesh_mat_source_objects if bpy.data.objects.get(sop.name) is None]) > 0) and \
            (len([sop for sop in context.scene.mesh_mat_source_collections if bpy.data.collections.get(sop.name) is None]) > 0):
            self.report({'ERROR_INVALID_INPUT'}, 'No existing source objects selected for target object.')
            return {'CANCELLED'}

        msgs = validate_target_obj(context.active_object)
        if len(msgs) > 0:
            self.report({'ERROR_INVALID_INPUT'}, 'Invalid Target Object: ' + ','.join(msgs))
            return {'CANCELLED'}

        # context.window.cursor_set("PAINT_BRUSH")
        self.is_drawing = False
        self.faces = []
        self.draw_faces = {}
        self.draw_verts = {}
        self.draw_edges = {}
        self.paint_mode = 'ADD'
        self._region = context.region
        self.target_object = context.active_object

        self.region = context.region
        self.rv3d = context.space_data.region_3d

        self.matrix_world_inv = context.active_object.matrix_world.inverted()
        self.rotation_euler_inverted = context.active_object.rotation_euler.to_matrix().inverted()

        # Depending on the context, face detection and bmesh generation have to be different.
        if context.active_object.mode == 'EDIT':
            bm_target = bmesh.from_edit_mesh(context.active_object.data).copy()
        elif context.active_object.mode == 'OBJECT':
            bm_target = bmesh.new()
            bm_target.from_object(context.active_object, depsgraph=context.evaluated_depsgraph_get(), face_normals=True)
        
        self.bvhtree = BVHTree.FromBMesh(bm_target, epsilon=0.00001)

        self.bm_target = bm_target
       
        context.window_manager.modal_handler_add(self)

        #draw a framing user interface for generating the mesh before commiting to it.
        if context.area.type == 'VIEW_3D':
            self._handle_3d = bpy.types.SpaceView3D.draw_handler_add(ui.draw_callback_3d, (self, context), 'WINDOW', 'POST_VIEW')

        MeshMaterializer_OT_ModalOperator.running_mesh_materializers[self._region] = self

        return {'RUNNING_MODAL'}

    @classmethod
    def poll(cls, context):
        return main_tool_poll(context)

def main_tool_poll(context):
    general_props, source_objects_props = invoke_props(context)

    return (len(source_objects_props) > 0) and \
            (context.active_object and \
            ((context.active_object.type == 'MESH' and \
            context.active_object.mode == 'OBJECT') or \
            (context.active_object.type == 'MESH' and \
            context.active_object.mode == 'EDIT' and \
            context.scene.tool_settings.mesh_select_mode[2])))

def get_new_MeshMaterializerCustomProperty(obj):
    return MeshMaterializerCustomProperty(
                obj.name,
                obj.is_enabled,
                obj.use_custom_parameters,
                obj.randomize_parameters,
                obj.randomize_parameters_seed,
                obj.location,
                obj.scale_x,
                obj.scale_y,
                obj.scale_z,
                obj.rotate,
                obj.location_rand,
                obj.scale_x_rand,
                obj.scale_y_rand,
                obj.scale_z_rand,
                obj.rotate_rand,
                obj.maintain_proportions,
                obj.align_normal,
                int(obj.align_normal_type),
                obj.normal_height,
                int(obj.obj_pos),
                obj.custom_normal
            )

def invoke_props(context):
    """Creates property value objects from the options in the add-on."""

    # General properties.
    general_props = MeshMaterializerGeneralProperty(
        context.scene.mesh_mat_tiles_across,
        context.scene.mesh_mat_tiles_down,
        context.scene.mesh_mat_randomize_parameters,
        context.scene.mesh_mat_randomize_parameters_seed,
        context.scene.mesh_mat_location,
        context.scene.mesh_mat_scale_x,
        context.scene.mesh_mat_scale_y,
        context.scene.mesh_mat_scale_z,
        context.scene.mesh_mat_rotate,
        context.scene.mesh_mat_location_rand,
        context.scene.mesh_mat_scale_x_rand,
        context.scene.mesh_mat_scale_y_rand,
        context.scene.mesh_mat_scale_z_rand,
        context.scene.mesh_mat_rotate_rand,
        context.scene.mesh_mat_maintain_proportions,
        context.scene.mesh_mat_align_normal,
        int(context.scene.mesh_mat_align_normal_type),
        context.scene.mesh_mat_normal_height,
        int(context.scene.mesh_mat_obj_pos),
        context.scene.mesh_mat_custom_normal
    )

    # Source object specific properties.
    source_objects_props = []
    for obj in context.scene.mesh_mat_source_objects:
        if obj.is_enabled and bpy.data.objects.get(obj.name) is not None:
            source_obj_prop = get_new_MeshMaterializerCustomProperty(obj)
            source_objects_props.append(source_obj_prop)

    for col_prop in context.scene.mesh_mat_source_collections:
        if col_prop.is_enabled and bpy.data.collections.get(col_prop.name) is not None:
            for obj in col_prop.source_objects:
                if obj.is_enabled and bpy.data.objects.get(obj.name) is not None:
                            source_obj_prop = get_new_MeshMaterializerCustomProperty(obj)
                            source_objects_props.append(source_obj_prop)

    return general_props, source_objects_props

def validate_target_obj(obj):
    """Validates the target object to check if it is viable for processing."""
    msgs = []
    if obj is None:
        msgs.append("No target object found.")
    elif len(obj.data.uv_layers) == 0:
        msgs.append("No UV Layers found")
    return msgs

import os

_accepted_types = {'MESH', 'FONT', 'EMPTY'}
_modifier_name = "Mesh Materializer Node v1.0"

def _nodes_op_poll(context):
    global _accepted_types
    return context.mode == 'OBJECT' and (context.active_object and len([o for o in context.selected_objects if o.type in _accepted_types]) > 1)

    
class MESH_OT_AddMeshMatGeoNodesOperator(bpy.types.Operator):
    """Add a mesh that wraps a Source Object to a Target Object UV Map"""
    bl_idname = "view3d.add_meshmat_geonodes"
    bl_label = "Create UV Mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        global _nodes_op_poll
        return _nodes_op_poll(context)

    def invoke(self, context, event):
        """Invoke the addon"""






        if bpy.app.version < (3, 4, 0):
            self.report({'ERROR'}, 'This operation requires Blender 3.4 or above.')
            return {'CANCELLED'}

        return self.execute(context)

    def execute(self, context):

        global _modifier_name

        user_preferences = context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences

        blend_file = 'mesh_mat_geonodes.blend'

        file_path = os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources'), blend_file)

        if _modifier_name in bpy.data.node_groups and bpy.data.node_groups[_modifier_name].users == 0:
            bpy.data.node_groups.remove(bpy.data.node_groups[_modifier_name])

        with bpy.data.libraries.load(file_path) as (data_from, data_to):

            data_to.node_groups = [ng for ng in data_from.node_groups if ng not in bpy.data.node_groups]

            data_to.texts = [text for text in data_from.texts if text not in bpy.data.texts]

        
        if _modifier_name not in bpy.data.node_groups:
            self.report({'ERROR'}, "Cannot find Mesh Materializer Node Group")
            return {'CANCELLED'}


        # assign modifier and node group to object
        target_object = context.active_object


        global _accepted_types
        source_objects = [o for o in context.selected_objects if o.type in _accepted_types and o != target_object]


        for source_object in source_objects:


            new_obj_name = source_object.name + ' - ' + target_object.name + ' UV Mesh'
            mesh = bpy.data.meshes.new(new_obj_name)
            new_obj = bpy.data.objects.new(new_obj_name, mesh)
            new_obj.location = target_object.location
            collection = target_object.users_collection[0] if len(target_object.users_collection) else context.collection
            collection.objects.link(new_obj)

            new_obj.color = source_object.color


            mod = new_obj.modifiers.new(name='Mesh Materializer', type='NODES')

            mod.node_group = bpy.data.node_groups[_modifier_name]


            identifier = mod.node_group.inputs['Source Object'].identifier
            mod[identifier] = source_object

            identifier = mod.node_group.inputs['Target Object'].identifier
            mod[identifier] = target_object


            active_uv_map = target_object.data.uv_layers.active

            if not active_uv_map:
                self.report({'WARNING'}, "Target Object has no active UV MAP")
                continue

            identifier = mod.node_group.inputs['Target Object UV Map'].identifier
            mod[identifier] = active_uv_map.name

            context.view_layer.objects.active = new_obj
            for selected_object in context.selected_objects:
                selected_object.select_set(False)

            new_obj.select_set(True)
    
        
        target_object.update_tag()

        return {'FINISHED'}


class OBJECT_MT_mesh_mat(bpy.types.Menu):
    bl_idname = 'OBJECT_MT_mesh_mat'
    bl_label = 'Mesh Materializer'

    def draw(self, context):
        layout = self.layout
        layout.operator(MESH_OT_AddMeshMatGeoNodesOperator.bl_idname, icon='UV_DATA')
        


def menu_func(self, context):
    self.layout.menu(OBJECT_MT_mesh_mat.bl_idname)

def meshmat_quick_func(self, context):
    if hasattr(context, 'active_object') and context.active_object and context.active_object.mode == 'OBJECT':
        col = self.layout.column()
        col.operator(MESH_OT_AddMeshMatGeoNodesOperator.bl_idname, icon='UV_DATA', text="")