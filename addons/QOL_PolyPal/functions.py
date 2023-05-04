import bpy,bmesh,math,gpu
from . import overlay
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
from mathutils import Euler, Vector,Quaternion
from mathutils.geometry import intersect_line_plane
from bpy_extras.view3d_utils import (
    region_2d_to_vector_3d,
    region_2d_to_origin_3d,
    region_2d_to_location_3d,
    )
from .prefs import QOLPolyPal_get_preferences
from mathutils.bvhtree import BVHTree


def redrawMesh(self,context):
    bmNew = bmesh.new()
    for v in self.vertices:
        bmNew.verts.new(v)
    bmNew.verts.ensure_lookup_table()
    if len(self.vertices) == 2:
        bmNew.edges.new((bmNew.verts[0],bmNew.verts[1]))
    if len(self.vertices) >= 3:
        bmNew.faces.new(bmNew.verts)
    bpy.ops.object.mode_set(mode='OBJECT')
    bmNew.to_mesh(self.mesh)
    bmNew.free()
    bpy.ops.object.mode_set(mode='EDIT')
    if self.objectViewMode:
        bpy.ops.object.mode_set(mode='OBJECT')

def rebuildMeshListData(self,context):
    self.vertices = []
    self.screenVtcs = []
    obj = context.active_object
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        self.vertices.append(obj.matrix_world @ v.co)
        self.screenVtcs.append(convert_world_to_screen_coords(self.vertices[-1], context))
    bm.free()

def rebuildListDataFromFaces(self,context):
    self.vertices = []
    self.screenVtcs = []
    obj = context.active_object
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces.ensure_lookup_table()
    for face in bm.faces:
        for loop in face.loops:
            self.vertices.append(obj.matrix_world @ loop.vert.co)
            self.screenVtcs.append(convert_world_to_screen_coords(self.vertices[-1], context))

def convert_world_to_screen_coords(world_coords, context):
    try:
        region = context.region
        rv3d = context.space_data.region_3d
        screen_coords = view3d_utils.location_3d_to_region_2d(region, rv3d, world_coords)
        return int(screen_coords[0]), int(screen_coords[1])
    except:
        return 0,0

def convert_screen_to_world_coords(screen_coords, context):
    region = context.region
    rv3d = context.space_data.region_3d
    world_coords = view3d_utils.region_2d_to_location_3d(region, rv3d, screen_coords, (0, 0, 0))
    return world_coords

def get_origin_and_direction(self, event, context, raycheck=True):
    region    = context.region
    region_3d = context.space_data.region_3d
    mouse_coord = (event.mouse_region_x, event.mouse_region_y)
    origin    = region_2d_to_origin_3d(region, region_3d, mouse_coord)
    pos    = region_2d_to_location_3d(region, region_3d, mouse_coord,(0, 0, 0))
    direction = region_2d_to_vector_3d(region, region_3d, mouse_coord)
    if raycheck:
        return origin, direction
    else:
        return pos, direction

def get_normal_on_mesh(self, event, context):
    
    origin, direction = get_origin_and_direction(self,event, context, raycheck=True)

    self.hit, self.normal, *_ = self.bvhtree.ray_cast(origin, direction)
    

    if self.hit is not None:
        self.hit = self.hit + (self.normal * self.offset)
    return self.hit, self.normal

def bvhtree_from_object(self, context, object):
    bm = bmesh.new()

    depsgraph = context.evaluated_depsgraph_get()
    ob_eval = object.evaluated_get(depsgraph)
    mesh = ob_eval.to_mesh()

    bm.from_mesh(mesh)
    bm.transform(object.matrix_world)

    bvhtree = BVHTree.FromBMesh(bm)
    ob_eval.to_mesh_clear()
    return bvhtree


def get_mouse_3d_on_mesh(self, event, context):
    origin, direction = get_origin_and_direction(self,event, context, raycheck=True)
    scene = context.scene
    success, hit_location, hit_normal, face_index, object, matrix_world = scene.ray_cast(bpy.context.view_layer.depsgraph, origin, direction)
    if success:
        self.hit = hit_location
        self.csr =  hit_location
        self.normal = hit_normal
    else:
        #are we in perspective mode?
        if context.space_data.region_3d.view_perspective == 'PERSP':
            self.hit = intersect_line_plane(origin, origin + direction,self.hit,self.normal)
            self.csr = self.hit
        else:
            hitPos, direction = get_origin_and_direction(self,event, context, raycheck=False)
            self.normal = direction
            self.hit = hitPos + (direction * self.offset)
            self.csr = hitPos + (direction * self.offset)
    return self.hit

def get_mouse_3d_on_plane(self, event, context):
    origin, direction = get_origin_and_direction(self,event,context)
    planeHitPoint = intersect_line_plane(origin, origin + direction,self.hit,self.normal)
    self.csr = planeHitPoint
    return planeHitPoint

















def mBevel(self,context,finalize=False):
    redrawMesh(self,context)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(self.mesh)
    bm.verts.ensure_lookup_table()
    selected_vert = bm.verts[-1]
    bmesh.ops.bevel(
        bm,
        geom=[selected_vert],
        offset=self.bevelRadius,   
        segments=self.bevelSegments,  
        profile=0.5,   
        affect='VERTICES',
        loop_slide=True,
        )
    bm.verts.ensure_lookup_table()
    bmesh.update_edit_mesh(self.mesh)
    if self.objectViewMode:
        bpy.ops.object.mode_set(mode='OBJECT')

def GPUCircleDraw(self,context,coords, radius, color, width):
    vertices = []
    sides = 24
    for i in range(sides):
        vertices.append((coords[0]+radius*math.cos(i*2*math.pi/(sides*0.5)),coords[1]+radius*math.sin(i*2*math.pi/(sides*0.5))))
        colors = [color] * len(vertices)
    indices = []
    for i in range(sides):
        indices.append((i, (i+1)%sides))
    GPURender(width,colors,vertices,indices)

def GPULineDraw(self,context,coords1,coords2,color,width):
    vertices = [coords1,coords2]
    colors = [color] * len(vertices)
    indices = [(0,1)]
    GPURender(width,colors,vertices,indices)

def GPURender(width,colors,vertices,indices):
    shader = gpu.shader.from_builtin('SMOOTH_COLOR')
    originalGPULineWidth = gpu.state.line_width_get()
    gpu.state.line_width_set(width)
    batch = batch_for_shader(shader, 'LINES', {"pos": vertices, "color": colors}, indices=indices)
    shader.bind()
    batch.draw(shader)
    gpu.state.line_width_set(originalGPULineWidth)
    gpu.state.blend_set('NONE')

def legalDualOrthoCheck(context):
        legal = False
        camera = bpy.context.scene.camera
        viewport = bpy.context.space_data
        if camera is not None and camera.type == 'ORTHO' and camera.is_ortho():
            legal = True
        elif viewport.region_3d.view_perspective == 'ORTHO':
            legal = True
        if context.active_object is not None:
            if context.active_object.type == 'MESH':
                legal = True
        selectedObjects = context.selected_objects
        for obj in selectedObjects:
            if obj.type != 'MESH':
                legal = False
        if len(selectedObjects) <2:
            legal = False
        return legal

def orthoCheck(context):
        orthoView = False
        camera = bpy.context.scene.camera
        viewport = bpy.context.space_data
        if camera is not None and camera.type == 'ORTHO' and camera.is_ortho():
            orthoView = True
        elif viewport.region_3d.view_perspective == 'ORTHO':
            orthoView = True
        return orthoView


def makeBMCircle(self,context,update,angle=0):
    bpy.ops.object.mode_set(mode='EDIT')
    radius = self.radius
    obj = context.active_object
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    if update:
        for v in bm.verts:
            bm.verts.remove(v)
    for i in range(self.numSides):
        pointCoords = view3d_utils.region_2d_to_location_3d(
            context.region, context.space_data.region_3d,
            (self.InitialScreenMouseX+math.cos(i*2*math.pi/self.numSides+angle)*radius,self.InitialScreenMouseY+math.sin(i*2*math.pi/self.numSides+angle)*radius),
                (0, 0, 0))
        bm.verts.new(pointCoords)
    bm.verts.ensure_lookup_table()
    bm.faces.new(bm.verts)
    bmesh.update_edit_mesh(mesh)
    bpy.ops.object.mode_set(mode='OBJECT')
    context.area.tag_redraw()


def finalise(self,context,objAvailable):
    overlay.KillQOLHud()
    context.area.tag_redraw()
    if objAvailable:
        initialMode = context.active_object.mode
        obj = bpy.context.active_object
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        face = bm.faces[0]
        # local_center = face.calc_center_median()
        local_normal = face.normal
        world_normal = (obj.matrix_world.to_3x3() @ local_normal).normalized()
        cursor_rotation = world_normal.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.scene.cursor.rotation_euler = cursor_rotation
        context.scene.tool_settings.use_transform_data_origin = True # origins only ("D"Key)
        bpy.ops.transform.transform(mode='ALIGN',
                                    orient_type='CURSOR',
                                    orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                                    orient_matrix_type='LOCAL',
                                    constraint_axis=(True, True, True),
                                    use_proportional_projected=False, snap=False,
                                    )
        context.scene.tool_settings.use_transform_data_origin = False # back to normal
        # bpy.context.scene.cursor.location = obj.matrix_world @ local_center
        bm.free()
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        bpy.ops.object.mode_set(mode=initialMode)
        bpy.ops.view3d.snap_cursor_to_center()

    return {'FINISHED'}

def getGridSize(context):
    prefs = QOLPolyPal_get_preferences(context)
    screenWidth = context.area.width
    screenHeight = context.area.height
    bottomleft = 0, 0
    topright = screenWidth, screenHeight
    BottomLeft3D = convert_screen_to_world_coords( bottomleft, context)
    TopRight3D = convert_screen_to_world_coords( topright, context)
    Diagonal = (TopRight3D - BottomLeft3D).length
    GSize = .01
    if Diagonal <0.2:
        GSize = .001
    if Diagonal >1 :
        GSize = .01
    if Diagonal > 5:
        GSize = .1
    if Diagonal > 25:
        GSize = .5
    if Diagonal > 50:
        GSize = 1
    if Diagonal > 200:
        GSize = 10
    if Diagonal > 5000:
        GSize = 100
    GSize = GSize * prefs.gridSize
    return GSize
