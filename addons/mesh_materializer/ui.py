import bpy
import bmesh
from . import props
from . import operators
from mathutils import Vector
# import bgl
import gpu
from gpu_extras.batch import batch_for_shader

class MeshMaterializer_PT_Panel(bpy.types.Panel):
    """Main Properties Panel"""
    bl_idname = "MESHMATERIALIZER_PT_Panel"
    bl_label = "Mesh Materializer"
    bl_category = "Mesh Materializer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(cls, context):
        user_preferences = context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences

        return addon_prefs.enable_legacy_version

    def draw(self, context):
        pass

class MeshMaterializer_PT_GeneralPanel(bpy.types.Panel):
    """General Properties Panel"""
    bl_idname = "MESHMATERIALIZER_PT_Panel_General"
    bl_label = "General"
    bl_category = "Mesh Materializer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = 'MESHMATERIALIZER_PT_Panel'

    def draw(self, context):
        layout = self.layout
        main_col = layout.column()



        main_col.label(text="Tiles")
        main_col.separator()
        main_col.prop_menu_enum(context.scene, "mesh_mat_pattern_type", 
                        text=props.pattern_items[int(getattr(context.scene, "mesh_mat_pattern_type"))][1])
        main_col.separator()
        main_col.prop(context.scene, "mesh_mat_random_seed", text="Random Seed")
        main_col.prop(context.scene, "mesh_mat_tiles_across", text="Tiles Across")
        main_col.prop(context.scene, "mesh_mat_tiles_down", text="Tiles Down")

        main_col.separator()

        render_settings(main_col, context.scene, prop_prefix="mesh_mat_")

class MeshMaterializer_PT_AdvancedPanel(bpy.types.Panel):
    """General Properties Panel"""
    bl_idname = "MESHMATERIALIZER_PT_Panel_Advanced"
    bl_label = "Advanced"
    bl_category = "Mesh Materializer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = 'MESHMATERIALIZER_PT_Panel'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        main_col = layout.column()
        main_col.separator()
        main_col.label(text="Mesh Creation approach:")
        main_col.prop_menu_enum(context.scene, "mesh_mat_approach", 
                        text=props.approach_items[int(getattr(context.scene, "mesh_mat_approach"))][1])
        main_col.separator()
        main_col.prop(context.scene, "mesh_mat_select_cut_geom")
        main_col.separator()
        main_col.prop(context.scene, "mesh_mat_add_edge_split", text="Add Edge Split Modifier")
        main_col.separator()
        int_mode_col = main_col.column()
        int_mode_col.enabled = not context.scene.mesh_mat_toggle
        int_mode_col.prop(context.scene, "mesh_mat_interactive_mode", text="Parameters Update Selection")

def render_source_obj(box, source_object, remove_op_id, id_to_remove, col_id=-1):
    row = box.row()
    row.prop(source_object, 'is_enabled', text="")
    name_col = row.column()
    name_col.alert = bpy.data.objects.get(source_object.name) is None
    name_col.label(text=source_object.name)
    
    row.prop(source_object, 'use_custom_parameters', text="", icon="MENU_PANEL")
    op_props = row.operator(remove_op_id, text="", icon="CANCEL")
    op_props.id_to_remove = id_to_remove
    if col_id >= 0:
        op_props.col_id = col_id

    if source_object.use_custom_parameters:
        col = box.column()
        col.enabled = source_object.is_enabled
        render_settings(box, source_object)
                
class MeshMaterializer_PT_ObjectsPanel(bpy.types.Panel):
    """Properties panel for objects"""
    bl_idname = "MESHMATERIALIZER_PT_Panel_Objects"
    bl_label = "Source Objects"
    bl_category = "Mesh Materializer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = 'MESHMATERIALIZER_PT_Panel'

    def draw(self, context):
        layout = self.layout
        main_col = layout.column()
        
        if len(context.scene.mesh_mat_source_objects) == 0 and len(context.scene.mesh_mat_source_collections) == 0:
            alert_col = main_col.column()
            alert_col.alert = True
            alert_col.label(text="No objects added")

        elif len([sop for sop in context.scene.mesh_mat_source_objects if sop.is_enabled]) == 0 and \
                len([sop for sop in context.scene.mesh_mat_source_collections if sop.is_enabled]) == 0:
            alert_col = main_col.column()
            alert_col.alert = True
            alert_col.label(text="No enabled objects")

        if len([sop for sop in context.scene.mesh_mat_source_objects if bpy.data.objects.get(sop.name) is None]) > 0:
            alert_col = main_col.column()
            alert_col.alert = True
            alert_col.label(text="Objects are not present in list")

        if len([sop for sop in context.scene.mesh_mat_source_collections if bpy.data.collections.get(sop.name) is None or \
                len(sop.source_objects) == 0]) > 0:
            alert_col = main_col.column()
            alert_col.alert = True
            alert_col.label(text="Invalid collections found")

        main_col.label(text="Objects")
        main_col.separator()
        row = main_col.row()
        row.prop(context.scene, "mesh_mat_object_to_add", text="Add")
        row.operator('view3d.mesh_materializer_add_scene_object', text="", icon="PLUS")
            
        
        i=0
        for source_object in context.scene.mesh_mat_source_objects:
            box = main_col.box()
            render_source_obj(box, source_object, 'view3d.mesh_materializer_remove_scene_object', i)
            i+=1

        main_col.label(text="Collections")
        main_col.separator()
        row = main_col.row()
        row.prop(context.scene, "mesh_mat_collection_to_add", text="Add")
        row.operator('view3d.mesh_materializer_add_scene_collection', text="", icon="PLUS")

        c = 0
        for source_collection in context.scene.mesh_mat_source_collections:
            box = main_col.box()
            
            row = box.row()
            row.prop(source_collection, 'is_enabled', text="")
            name_col = row.column()
            name_col.alert = bpy.data.collections.get(source_collection.name) is None
            name_col.label(text=source_collection.name)
            op_props = row.operator('view3d.mesh_materializer_remove_scene_collection', text="", icon="CANCEL")
            op_props.collection_to_remove = source_collection.name
            
            source_props_box = box.column()
            i=0
            for source_object in source_collection.source_objects:
                source_prop_box = source_props_box.box()
                render_source_obj(source_prop_box, source_object, 'view3d.mesh_materializer_remove_scene_object_col', i, c)
                i+=1
            c+=1

        main_col.separator()
class MeshMaterializer_PT_OperatorsPanel(bpy.types.Panel):
    """Properties panel for add-on operators."""
    bl_idname = "MESHMATERIALIZER_PT_Panel_Operators"
    bl_label = "Operations"
    bl_category = "Mesh Materializer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = 'MESHMATERIALIZER_PT_Panel'

    def draw(self, context):
        col = self.layout.column()
        no_active_obj = context.active_object is None
        if no_active_obj:
            target_object_name = "No target object selected"
        else:
            target_object_name = context.active_object.name
        col.label(text="Target Object: ")
        name_col = col.column()
        name_col.alert = no_active_obj
        name_col.label(text=target_object_name)

        op_col = col.column()
        user_preferences = context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences
        if not no_active_obj and \
            context.active_object.type == 'MESH' and \
            ((len(context.active_object.data.polygons) > addon_prefs.poly_count_check and \
                context.active_object.mode == 'OBJECT')  or \
                    (  context.active_object.mode == 'EDIT' and \
                        len([f for f in bmesh.from_edit_mesh(context.active_object.data).faces if f.select]) > addon_prefs.poly_count_check )   )   :
            op_col.operator('view3d.mesh_materializerconfirm', text='Apply to Selection', icon='OUTLINER_OB_LATTICE')
        else:
            op_col.operator('view3d.mesh_materializer', text='Apply to Selection', icon='OUTLINER_OB_LATTICE')
            
        col.operator('view3d.mesh_materializer_delete_selection', text='Delete from Selection', icon='LATTICE_DATA')
        label = "Paint (ESCAPE to finish)" if context.scene.mesh_mat_toggle else "Paint"
        col.separator()
        paint_col = col.column()
        paint_col.enabled = not no_active_obj and operators.main_tool_poll(context) and not context.scene.mesh_mat_interactive_mode
        paint_col.prop(context.scene, 'mesh_mat_toggle', text=label, toggle=True, icon='BRUSH_DATA')
        paint_brush_col = paint_col.column()
        paint_brush_col.prop(context.scene, 'mesh_mat_brush_size', text="Brush Size")
        
 
        col.separator()
        col.label(text="Materialized Object: ")
        col.operator('view3d.mesh_materializer_dissolve_geom', text='Dissolve Cuts', icon='GROUP_VCOL')
        col.operator('view3d.mesh_materializer_remove_doubles', text='Merge Vertices', icon='GROUP_VERTEX')
        col.operator('view3d.mesh_materializer_fill_holes', text='Fill Holes', icon='SELECT_EXTEND')
        col.operator('view3d.mesh_materializer_remove_cut_objects', text='Remove Sliced Objects', icon='MOD_BOOLEAN')
        col.operator('view3d.mesh_materializer_recalc_normals', text='Recalculate Normals', icon='NORMALS_FACE')
        col.operator('mesh.tris_convert_to_quads', text='Tris to Quads', icon='RIGID_BODY')


def render_settings(layout, container, prop_prefix=""):
    """Display source object properties depending on the origin (e.g. from context.scene or from the operator."""
    col = layout.column()
    randomize = getattr(container, prop_prefix + "randomize_parameters")

    row = col.row()
    row.column().prop(container, prop_prefix + "location", text="Object Offset")
    if (randomize):
        row.column().prop(container, prop_prefix + "location_rand", text="+/-")

    col.separator()
    row = col.row()
    row.column().prop(container, prop_prefix + "rotate", text="Object Rotate")
    if (randomize):
        row.column().prop(container, prop_prefix + "rotate_rand", text="+/-")


    col.separator()
    col.label(text="Object Scale: ")

    row = col.row()
    row.prop(container, prop_prefix + "scale_x", text="X:")
    if (randomize):
        row.prop(container, prop_prefix + "scale_x_rand")
    row = col.row()
    row.prop(container, prop_prefix + "scale_y", text="Y:")
    if (randomize):
        row.prop(container, prop_prefix + "scale_y_rand")
    row = col.row()
    row.prop(container, prop_prefix + "scale_z", text="Z:")
    if (randomize):
        row.prop(container, prop_prefix + "scale_z_rand")



    col.separator()
    col.prop(container, prop_prefix + "maintain_proportions")
    col.separator()
    col.prop(container, prop_prefix + "randomize_parameters", text="Randomize Parameters")
    randomize_seed_col = col.column()
    randomize_seed_col.enabled = randomize
    randomize_seed_col.prop(container, prop_prefix + "randomize_parameters_seed")

    col.separator()
    col.prop(container, prop_prefix + "align_normal", text="Normal Alignment")
    align_col = col.column()
    align_col.enabled = getattr(container, prop_prefix + "align_normal")
    align_col.prop_menu_enum(container, prop_prefix + "align_normal_type", 
                        text=props.align_normal_type_items[int(getattr(container, prop_prefix + "align_normal_type"))][1])

    if getattr(container, prop_prefix + "align_normal"):
        align_col.prop(container, prop_prefix + "normal_height", text="Normal Multiplier")

    if getattr(container, prop_prefix + "align_normal_type") == '2':
        align_col.prop(container, prop_prefix + "custom_normal")

    col.separator()
    col.label(text="Object Position:")
    col.prop_menu_enum(container, prop_prefix + 'obj_pos',
                text=props.obj_pos_items[int(getattr(container, prop_prefix + "obj_pos"))][1])

    


def draw_callback_3d(self, context):
    """Draw a 3D representaion of the mesh for a preview."""
    try:
        if not (operators.MeshMaterializer_OT_ModalOperator.running_mesh_materializers.get(self._region) is self): return
        if not hasattr(self, 'draw_verts'): return

        user_preferences = context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences

        face_color = addon_prefs.add_face_color if self.paint_mode == 'ADD' else addon_prefs.del_face_color

        # bgl.glEnable(bgl.GL_BLEND)
        gpu.state.blend_set("ALPHA")

        coords = [self.draw_verts[i] for i in self.draw_verts.keys()]

        # Draw Edges
        indices = self.draw_edges.values()
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

        batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices= indices)
        shader.bind()
        shader.uniform_float("color", face_color)
        batch.draw(shader)

        # Draw faces
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        indices = []
        for face_index in self.draw_faces.keys():
            face_vert_indexes = self.draw_faces[face_index]['vert_indexes']
            iv0 = face_vert_indexes[0]
            for iv1,iv2 in zip(face_vert_indexes[1:-1], face_vert_indexes[2:]):
                indice = (iv0, iv1, iv2)
                indices.append(indice)
        batch = batch_for_shader(shader, 'TRIS', {"pos": coords}, indices= indices)
        shader.bind()
        shader.uniform_float("color", face_color)
        batch.draw(shader)

        # bgl.glDisable(bgl.GL_BLEND)
        gpu.state.blend_set("NONE")

    except ReferenceError as re:
        pass