bl_info = {
    "name": "Mesh Cleaner",
    "blender": (2, 80, 0),
    "category": "Mesh",
    "description": "A tool to clean up geometry. Activated in the N-panel and Object context menu",
    "author": "Rob Dickinson"
}

import bpy
import bmesh
from mathutils import Vector

# Utility function to update triangle count
def update_triangle_count(context):
    obj = context.active_object
    if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        context.scene.triangle_count = sum(1 for f in bm.faces if len(f.verts) == 3)
        context.scene.tri_count = sum(1 for f in bm.faces if len(f.verts) == 3) # Also update tri_count
    else:
        context.scene.triangle_count = 0  # Reset count when not in Edit Mode
        context.scene.tri_count = 0
        

# Operators
class MESH_OT_CheckDoubles(bpy.types.Operator):
    bl_idname = "mesh.check_doubles"
    bl_label = "Check Doubles"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        thresh = context.scene.double_threshold
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        verts = bm.verts[:]
        double_verts = set()

        for i, v1 in enumerate(verts):
            for v2 in verts[i + 1:]:
                if (v1.co - v2.co).length < thresh:
                    double_verts.add(v1)
                    double_verts.add(v2)

        context.scene.double_count = len(double_verts)
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class MESH_OT_CustomRemoveDoubles(bpy.types.Operator):
    bl_idname = "mesh.custom_remove_doubles"
    bl_label = "Remove Doubles"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        thresh = context.scene.double_threshold
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=thresh)

        bmesh.update_edit_mesh(obj.data)
        context.scene.double_count = 0
        update_triangle_count(context)
        return {'FINISHED'}


class MESH_OT_CheckFlippedNormals(bpy.types.Operator):
    bl_idname = "mesh.check_flipped_normals"
    bl_label = "Check Flipped Normals"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.normal_update()

        flipped_faces = [f for f in bm.faces if not f.normal.dot(f.calc_center_median().normalized()) > 0]

        context.scene.flipped_normals_count = len(flipped_faces)
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class MESH_OT_FixFlippedNormals(bpy.types.Operator):
    bl_idname = "mesh.fix_flipped_normals"
    bl_label = "Fix Flipped Normals"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.mesh.check_flipped_normals()  # Update flipped face counter
        return {'FINISHED'}


class MESH_OT_RemoveLooseGeometry(bpy.types.Operator):
    bl_idname = "mesh.remove_loose_geometry"
    bl_label = "Remove Loose Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete_loose()
        update_triangle_count(context)
        return {'FINISHED'}


class MESH_OT_ConvertToQuads(bpy.types.Operator):
    bl_idname = "mesh.convert_to_quads"
    bl_label = "Convert to Quads"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.tris_convert_to_quads()
        update_triangle_count(context)
        return {'FINISHED'}

class MESH_OT_CheckTris(bpy.types.Operator):
    bl_idname = "mesh.check_tris"
    bl_label = "Check Tris"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(obj.data)
            tri_count = sum(1 for f in bm.faces if len(f.verts) == 3)
            context.scene.tri_count = tri_count
            context.scene.triangle_count = tri_count # Keep the triangle_count updated
            self.report({'INFO'}, f"Number of Tris: {tri_count}")
            bmesh.update_edit_mesh(obj.data)
        else:
            self.report({'WARNING'}, "Please select a mesh object in Edit Mode.")
            context.scene.tri_count = 0
            context.scene.triangle_count = 0
        return {'FINISHED'}


class MESH_OT_CheckHoles(bpy.types.Operator):
    bl_idname = "mesh.check_holes"
    bl_label = "Check Holes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        boundary_edges = [e for e in bm.edges if e.is_boundary]
        visited = set()
        hole_loops = 0
        for edge in boundary_edges:
            if edge in visited:
                continue
            loop_edges = []
            current = edge
            start_vert = current.verts[0]
            vert = start_vert
            while True:
                loop_edges.append(current)
                visited.add(current)
                next_edge = None
                for e in vert.link_edges:
                    if e.is_boundary and e is not current:
                        next_edge = e
                        break
                if not next_edge or next_edge in loop_edges:
                    break
                vert = next_edge.other_vert(vert)
                current = next_edge
            hole_loops += 1
        context.scene.holes_status = f"{hole_loops} holes detected" if hole_loops > 0 else "No holes detected"
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class MESH_OT_FixHoles(bpy.types.Operator):
    bl_idname = "mesh.fix_holes"
    bl_label = "Fix Holes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        boundary_edges = [e for e in bm.edges if e.is_boundary]
        if boundary_edges:
            bmesh.ops.holes_fill(bm, edges=boundary_edges)
            context.scene.holes_status = "No holes detected"
        else:
            self.report({'INFO'}, "No holes to fill")
        bmesh.update_edit_mesh(obj.data)
        update_triangle_count(context)
        return {'FINISHED'}


class MESH_OT_RemoveUnusedMaterials(bpy.types.Operator):
    bl_idname = "mesh.remove_unused_materials"
    bl_label = "Remove Unused Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj.type != 'MESH':
            return {'CANCELLED'}
        mesh = obj.data
        used = {p.material_index for p in mesh.polygons}
        mode = obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        removed = 0
        for i in reversed(range(len(obj.material_slots))):
            if i not in used:
                obj.active_material_index = i
                bpy.ops.object.material_slot_remove()
                removed += 1
        bpy.ops.object.mode_set(mode=mode)
        self.report({'INFO'}, f"Removed {removed} unused materials")
        return {'FINISHED'}


class MESH_OT_CheckZFight(bpy.types.Operator):
    bl_idname = "mesh.check_zfight"
    bl_label = "Check Z-Fighting"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        thresh = context.scene.zfight_threshold
        for f in bm.faces:
            f.select = False
        faces = list(bm.faces)
        zfaces = set()
        for i, f1 in enumerate(faces):
            for f2 in faces[i + 1:]:
                if f1.normal.dot(f2.normal) > 0.999:
                    if (f1.calc_center_median() - f2.calc_center_median()).length < thresh:
                        zfaces.add(f1)
                        zfaces.add(f2)
        for f in zfaces:
            f.select = True
        context.scene.zfight_count = len(zfaces)
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class MESH_OT_QuickCleanUp(bpy.types.Operator):
    bl_idname = "mesh.quick_clean_up"
    bl_label = "Quick Clean Up"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.check_doubles()
        if context.scene.double_count > 0:
            bpy.ops.mesh.custom_remove_doubles()
        bpy.ops.mesh.convert_to_quads()
        bpy.ops.mesh.fix_flipped_normals()
        bpy.ops.mesh.remove_loose_geometry()
        bpy.ops.mesh.check_holes()
        if "holes detected" in context.scene.holes_status:
            bpy.ops.mesh.fix_holes()
        bpy.ops.mesh.remove_unused_materials()
        update_triangle_count(context)
        return {'FINISHED'}

class MESH_OT_RemoveParents(bpy.types.Operator):
    bl_idname = "mesh.remove_parents"
    bl_label = "Remove Parents"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        return {'FINISHED'}


class MESH_OT_RemoveEmptyCollections(bpy.types.Operator):
    bl_idname = "mesh.remove_empty_collections"
    bl_label = "Remove Empty Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collections_removed = 0
        for collection in bpy.data.collections:
            if not collection.objects:
                bpy.data.collections.remove(collection)
                collections_removed += 1
        self.report({'INFO'}, f"Removed {collections_removed} empty collections.")
        return {'FINISHED'}


class MESH_OT_RemoveUnattachedEmpties(bpy.types.Operator):
    bl_idname = "mesh.remove_unattached_empties"
    bl_label = "Remove Unattached Empties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_count = 0
        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY' and not obj.children and not any(
                    parent for parent in bpy.context.scene.objects if obj in parent.children):
                bpy.data.objects.remove(obj)
                removed_count += 1
        self.report({'INFO'}, f"Removed {removed_count} unattached empties.")
        return {'FINISHED'}


# Add this to the Object Mode Panel where the user can access it
class MESH_PT_MeshCleanerObjectModePanel(bpy.types.Panel):
    bl_label = "Mesh Cleaner"
    bl_idname = "MESH_PT_mesh_cleaner_object_mode"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mesh Cleaner'

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Switch to Edit Mode to access mesh tools")
        layout.operator("object.switch_to_edit_mode", icon='EDITMODE_HLT')

        layout.separator()
        layout.operator("mesh.remove_empty_collections")

        layout.separator()
        layout.operator("mesh.remove_unattached_empties")
        
        layout.separator()
        layout.operator("mesh.remove_parents")


class OBJECT_OT_SwitchToEditMode(bpy.types.Operator):
    bl_idname = "object.switch_to_edit_mode"
    bl_label = "Switch to Edit Mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        if obj.type != 'MESH':
            self.report({'WARNING'}, f"Object '{obj.name}' is not a mesh")
            return {'CANCELLED'}
        
        # Ensure object is selected and active
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Blender 5.0: Use direct mode assignment instead of operator
        # The mode_set operator enum changed in 5.0
        try:
            # Direct assignment works in all Blender versions
            context.object.mode = 'EDIT'
        except (AttributeError, TypeError, ValueError) as e:
            # Fallback: try operator method (for older versions)
            try:
                bpy.ops.object.mode_set(mode='EDIT')
            except (TypeError, ValueError):
                self.report({'ERROR'}, f"Could not switch to edit mode: {e}")
                return {'CANCELLED'}
        
        return {'FINISHED'}


class MESH_PT_MeshCleanerPanel(bpy.types.Panel):
    bl_label = "Mesh Cleaner"
    bl_idname = "MESH_PT_mesh_cleaner"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mesh Cleaner'

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.mode == 'EDIT'

    def draw(self, context):
        layout = self.layout

        layout.label(text="Double Geometry")
        layout.prop(context.scene, "double_threshold", text="Threshold")
        layout.operator("mesh.check_doubles", text="Check Doubles")

        double_count = context.scene.get('double_count', 0)
        if double_count > 0:
            layout.label(text=f"Doubles detected: {double_count}")
            layout.operator("mesh.custom_remove_doubles", text="Remove Doubles")
        else:
            layout.label(text="No doubles detected")

        layout.separator()
        layout.label(text="Triangles")
        layout.operator("mesh.check_tris", text="Check Tris")
        layout.label(text=f"Number of Tris: {context.scene.get('triangle_count', 0)}")
        layout.operator("mesh.convert_to_quads", text="Convert to Quads")

        layout.separator()
        layout.label(text="Flipped Normals")
        layout.operator("mesh.check_flipped_normals", text="Check Normals")

        flipped_normals_count = context.scene.get('flipped_normals_count', 0)
        layout.label(text=f"{flipped_normals_count} faces with flipped normals")

        if flipped_normals_count > 0:
            layout.operator("mesh.fix_flipped_normals", text="Fix Normals")

        layout.separator()
        layout.label(text="Holes")
        layout.operator("mesh.check_holes", text="Check Holes")
        holes_status = context.scene.get('holes_status', "No holes detected")
        layout.label(text=holes_status)
        layout.operator("mesh.fix_holes", text="Fix Holes")

        layout.separator()
        layout.label(text="Loose Geometry")
        layout.operator("mesh.remove_loose_geometry", text="Remove Loose Geometry")

        layout.separator()
        layout.label(text="Unused Materials")
        layout.operator("mesh.remove_unused_materials", text="Remove Unused Materials")

        layout.separator()
        layout.label(text="Z-Fighting")
        layout.prop(context.scene, "zfight_threshold", text="Threshold")
        layout.operator("mesh.check_zfight", text="Check Z-Fighting")
        zfight_count = context.scene.get('zfight_count', 0)
        layout.label(text=f"{zfight_count} potential Z-fighting faces")

        layout.separator()
        layout.operator("mesh.quick_clean_up", text="Quick Clean Up")


# Add Quick Clean Up to right-click menu
def menu_func(self, context):
    self.layout.operator(MESH_OT_QuickCleanUp.bl_idname, text="Quick Clean Up")


classes = [
    MESH_OT_CheckDoubles,
    MESH_OT_CustomRemoveDoubles,
    MESH_OT_CheckFlippedNormals,
    MESH_OT_FixFlippedNormals,
    MESH_OT_RemoveLooseGeometry,
    MESH_OT_ConvertToQuads,
    MESH_OT_CheckTris,
    MESH_OT_CheckHoles,
    MESH_OT_FixHoles,
    MESH_OT_RemoveUnusedMaterials,
    MESH_OT_CheckZFight,
    MESH_OT_QuickCleanUp,
    MESH_OT_RemoveEmptyCollections,
    MESH_OT_RemoveUnattachedEmpties,
    MESH_PT_MeshCleanerPanel,
    MESH_PT_MeshCleanerObjectModePanel,
    OBJECT_OT_SwitchToEditMode,
    MESH_OT_RemoveParents, # Add the new operator to the classes list.
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.double_count = bpy.props.IntProperty(default=0)
    bpy.types.Scene.flipped_normals_count = bpy.props.IntProperty(default=0)
    bpy.types.Scene.holes_status = bpy.props.StringProperty(default="No holes detected")
    bpy.types.Scene.double_threshold = bpy.props.FloatProperty(name="Double Threshold", default=0.0001, min=0.0, precision=6)
    bpy.types.Scene.zfight_threshold = bpy.props.FloatProperty(name="ZFight Threshold", default=0.001, min=0.0, precision=6)
    bpy.types.Scene.zfight_count = bpy.props.IntProperty(default=0)
    bpy.types.Scene.triangle_count = bpy.props.IntProperty(default=0)
    bpy.types.Scene.tri_count = bpy.props.IntProperty(default=0)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu_func)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.double_count
    del bpy.types.Scene.flipped_normals_count
    del bpy.types.Scene.holes_status
    del bpy.types.Scene.double_threshold
    del bpy.types.Scene.zfight_threshold
    del bpy.types.Scene.zfight_count
    del bpy.types.Scene.triangle_count
    del bpy.types.Scene.tri_count
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()
