bl_info = {
    "name": "Pixel Tracer",
    "author": "Miles",
    "description": "Trace image outline",
    "category": "Import-Export",
}

import bpy
import numpy as np
import bmesh
from mathutils import Vector

class ImportImagePanel(bpy.types.Panel):
    bl_label = "Pixel Tracer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pixel Tracer"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(context.scene, "my_image_path")
        
        layout.prop(context.scene, "black_threshold", slider=True)
        layout.prop(context.scene, "white_threshold", slider=True)
        
        row = layout.row()
        row = layout.box()
        row.scale_y = 2.0
        row.operator("object.import_image_button") 
        row = layout.row()
        layout.label(text="Refinement:")
        row = layout.row()
        layout.prop(context.scene, "cleanup_threshold", slider=True)      
        row = layout.row()        
        row.operator("object.clean_up_button")
        row = layout.box()          
        layout.prop(context.scene, "smooth_factor", slider=True)      
        layout.operator("object.smooth_vertices_button")
        
        row = layout.box()  
        layout.prop(context.scene, "max_distance", slider=True)
        row = layout.row() 
        row.operator("object.connect_remaining")

        row = layout.box()
        layout.prop(context.scene, "threshold", slider=True)
        layout.operator("bmesh.thresholdslider")
        row = layout.box()
        row = layout.row()
        row.operator("object.fill_function")

class ImportImageButton(bpy.types.Operator):
    """Import an image and create edge"""
    bl_idname = "object.import_image_button"
    bl_label = "Generate Edge"

    def execute(self, context):
        
        filepath = bpy.data.images.load(filepath=bpy.path.abspath(bpy.context.scene.my_image_path))
        img = filepath.pixels[:]
        width, height = filepath.size[0], filepath.size[1]
        img = np.array(img).reshape(height, width, 4)

        mesh = bpy.data.meshes.new("Silhouette Mesh")
        obj = bpy.data.objects.new("Silhouette", mesh)
        bpy.context.collection.objects.link(obj)

        verts = [(x, y, 0) for y in range(height)                   
        for x in range(width)                       
            if img[y][x][0] < context.scene.black_threshold 
                      and any(img[y+dy][x+dx][0] > context.scene.white_threshold 
                              for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)] 
                                  if (x+dx >= 0) and (x+dx < width) 
                                  and (y+dy >= 0) and (y+dy < height))]
        connected_edges = [0 for i in range(len(verts))]

        
        scale_factor = 0.05
        verts = [(x*scale_factor, y*scale_factor, z*scale_factor) for x, y, z in verts]

        mesh.from_pydata(verts, [], [])
        mesh.update()
        
        added_vertices = set()
       
        bm = bmesh.new()
        for i in range(len(verts)):
            if connected_edges[i] < 2:
                
                if tuple(verts[i]) in added_vertices:
                    continue
                added_vertices.add(tuple(verts[i]))
                vert1 = bm.verts.new(Vector(verts[i]))
                
                stack = [vert1]
                while stack:
                    vertex = stack.pop()
                    vert1 = Vector(vertex.co)
                    closest_distance = float("inf")
                    closest_index = None
                    for j in range(len(verts)):
                        if tuple(verts[j]) in added_vertices:
                            continue
                        vert2 = Vector(verts[j])
                        distance = (vert1 - vert2).length
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_index = j
                    if closest_index:
                        added_vertices.add(tuple(verts[closest_index]))
                        vert2 = bm.verts.new(Vector(verts[closest_index]))
                        edge = bm.edges.new([vertex, vert2])
                        stack.append(vert2)
        bm.to_mesh(mesh)

        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        obj.location = (0, 0, 0)

        mesh.update()
        
        return {'FINISHED'}
    
class CleanUpButton(bpy.types.Operator):
    """Removes edges that differ alot in length compared to all other edges"""
    bl_idname = "object.clean_up_button"
    bl_label = "Clean Up"
    cleanup_threshold: bpy.props.FloatProperty(
        name="cleanup_threshold",
        default=1,
        min=0,
        max=10,
        step=0.01,
        description="Threshold for edge length difference"
    )

    def execute(self, context):
        obj = bpy.context.active_object
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        total_length = 0
        for edge in bm.edges:
            total_length += edge.calc_length()
        avg_length = total_length / len(bm.edges)

        delete_edges = []
        for edge in bm.edges:
            if edge.calc_length() > context.scene.cleanup_threshold:
                delete_edges.append(edge)

        bmesh.ops.delete(bm, geom=delete_edges, context='EDGES')

        bm.to_mesh(mesh)
        mesh.update()
        bm.free()

        return {'FINISHED'}
    
class SmoothVerticesButton(bpy.types.Operator):
    """Smooth Vertices"""
    bl_idname = "object.smooth_vertices_button"
    bl_label = "Smooth Vertices"
    bpy.types.Scene.smooth_factor = bpy.props.FloatProperty(
        name="Smooth Factor",
        default=0.6,
        min=0,
        max=0.6,
        step=0.01
    )

    
    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.vertices_smooth(factor=context.scene.smooth_factor)
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Active object is not a Mesh")
            return {'CANCELLED'}


class ConnectRemaining(bpy.types.Operator):
    """Connect remaining edges"""
    bl_idname = "object.connect_remaining"
    bl_label = "Connect Remaining"
    bpy.types.Scene.max_distance = bpy.props.FloatProperty(
        name="Max Distance",
        default=1.0,
        min=0.01,
        max=10.0,
        step=0.01,
        precision=2,
        options={'ANIMATABLE'}
    )

    def execute(self, context):
        obj = bpy.context.active_object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        single_vertices = []
        for v in bm.verts:
            if len(v.link_edges) == 1:
                single_vertices.append(v)
                
        added_vertices = set()
        
        for v in single_vertices:
            if v in added_vertices:
                continue
            added_vertices.add(v)
            vert1 = v
            stack = [vert1]
            while stack:
                vertex = stack.pop()
                vert1 = Vector(vertex.co)
                closest_distance = float("inf")
                closest_vertex = None
                for v in single_vertices:
                    if v in added_vertices:
                        continue
                    vert2 = Vector(v.co)
                    distance = (vert1 - vert2).length
                    if distance < closest_distance and distance <= context.scene.max_distance:
                        closest_distance = distance
                        closest_vertex = v
                if closest_vertex:
                    added_vertices.add(closest_vertex)
                    vert2 = closest_vertex
                    edge = bm.edges.get([vertex, vert2])
                    if edge is None:
                        edge = bm.edges.new([vertex, vert2])
                    stack.append(vert2)
                    
        bm.to_mesh(obj.data)
        obj.data.update()
        
        return {'FINISHED'}
    
class FillFunction(bpy.types.Operator):
    """Create faces"""
    bl_idname = "object.fill_function"
    bl_label = "Fill"
    
    def execute(self, context):
        obj = bpy.context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.fill()

        bpy.ops.object.mode_set(mode='OBJECT')
        obj.data.update()

        num_faces_after = len(obj.data.polygons)
        if num_faces_after == 0:
            self.report({'ERROR'}, "Not all edges are connected.")
            return {'CANCELLED'}

        return {'FINISHED'}




class BMeshThresholdSlider(bpy.types.Operator):
    """Reduce vertice count on edge"""
    bl_label = "Reduce Vertices"
    bl_idname = "bmesh.thresholdslider"
    bpy.types.Scene.threshold = bpy.props.FloatProperty(
        name="Threshold", 
        default=0.01, 
        min=0.001, 
        max=1.0, 
        step=0.01
        )

    def execute(self, context):
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=context.scene.threshold)
        bm.to_mesh(obj.data)
        obj.data.update()
        bm.free()
        return {'FINISHED'}


bpy.utils.register_class(ImportImageButton)
bpy.utils.register_class(ImportImagePanel)
bpy.types.Scene.my_image_path = bpy.props.StringProperty(name="Image Path", subtype='FILE_PATH')
bpy.utils.register_class(CleanUpButton)
bpy.utils.register_class(SmoothVerticesButton)
bpy.utils.register_class(ConnectRemaining)
bpy.utils.register_class(BMeshThresholdSlider)
bpy.utils.register_class(FillFunction)
    

    
bpy.types.Scene.black_threshold = bpy.props.FloatProperty(name="Black Point Threshold", default=0.2, min=0, max=1)
bpy.types.Scene.white_threshold = bpy.props.FloatProperty(name="White Point Threshold", default=0.2, min=0, max=1)
bpy.types.Scene.cleanup_threshold = bpy.props.FloatProperty(name="Edge Length", default=1, min=0, max=1, step=0.01, description="Small values deletes short edges, large values delete long edges")
max_distance: bpy.props.FloatProperty(name="Max Distance", default=1.0, min=0.01, max=10.0, step=0.01, precision=2, options={'ANIMATABLE'})
threshold: bpy.props.FloatProperty(name="Threshold", default=0.01, min=0.001, max=0.1, step=0.01)