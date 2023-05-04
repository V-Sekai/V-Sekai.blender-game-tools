import bpy,bmesh,math,gpu,os
from copy import copy as copy
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_circle_2d
from bpy_extras import view3d_utils
from bpy.props import BoolProperty
from bpy.types import (Operator,Panel)
from mathutils import Vector
from .prefs import *
from . import functions
from . import overlay

ICONS = {
    "QOL_CutProject": "CutProject.png",
    "QOL_PolyPalDraw": "PolyPalDraw.png",
    "QOL_PolyPalRectangle": "PolyPalRectangle.png",
    "QOL_PolyPalCircle": "PolyPalCircle.png",
}
icons_dict = bpy.utils.previews.new()
icons_dir = os.path.join(os.path.dirname(__file__), "icons")
for icon_id, icon_file in ICONS.items():
    icons_dict.load(icon_id, os.path.join(icons_dir, icon_file), 'IMAGE')


class QOL_OT_PolyPalDraw(Operator):
    """Draws a polygon on the fly"""
    bl_idname = "qol.polypaldraw"
    bl_label = "QOL PolyPal Draw"
    bl_context = "mesh_edit"
    bl_options = {'REGISTER', 'UNDO'}

    directCreate : BoolProperty(name="Direct Create",default=False)

    def invoke(self,context,event):
        #get the current worspace tool id
        args = (self, context)
        prefs = QOLPolyPal_get_preferences(context)
        prefs.gridSize = round(prefs.gridSize,2)
        self.tool_id = context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname
        self.shader_leadingEdge = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        self.register_handlers(args, context)
        self.handler_handles = set()
        self.vertices = [] #list of 3d coordinates for the vertices
        self.screenVtcs = [] #list of 2d coordinates for the vertices
        self.create_batch_leading_edge()
        self.backup_manager = BackupManager()
        self.backup_manager.add_backup(self.vertices)
        self.undoProcess = False
        self.backupIndex = 1
        self.objectViewMode = False
        self.leftClick = False
        self.dotActive = False
        self.bevelling = False
        self.middleClick = False
        self.PostMMBRefresh = False
        self.drawFidelity = 100
        self.bevelSegments = 8
        self.bevelInitiated = False
        self.normal = Vector((0,0,1))
        self.hit = Vector((0,0,0))
        self.csr = Vector((0,0,0))
        self.offset = 0.02
        if not self.directCreate: #Attempting Edit Mode
            activeObject = context.active_object
            if activeObject is not None and activeObject.type == 'MESH' and activeObject.select_get():
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                self.mesh = context.active_object.data
                bpy.ops.object.mode_set(mode='EDIT')
                # functions.rebuildListDataFromFaces(self,context)
                bm = bmesh.from_edit_mesh(self.mesh)
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                faceCount = len(bm.faces)
                if faceCount > 1:
                    self.report({'INFO'}, "Mesh has unusable topology, please fix it first")
                    return {'CANCELLED'}    
                elif faceCount == 1:
                    self.hit = copy(bm.verts[0].co)
                    self.csr = copy(bm.verts[0].co)
                    self.normal = copy(bm.faces[0].normal)
                    activeObject.display_type = 'WIRE'

            else: #create a new mesh anyway if there is no active object selected
                self.mesh = bpy.data.meshes.new("QOL_PolyPalMesh")
                obj = bpy.data.objects.new("QOL_PolyPalPoly", self.mesh)
                context.collection.objects.link(obj)
                obj.select_set(True)
                obj.display_type = 'WIRE'
                context.view_layer.objects.active = obj
        else:
            self.mesh = bpy.data.meshes.new("QOL_PolyPalMesh")
            obj = bpy.data.objects.new("QOL_PolyPalPoly", self.mesh)
            context.collection.objects.link(obj)
            obj.select_set(True)
            obj.display_type = 'WIRE'
            context.view_layer.objects.active = obj

        overlay.draw_Hud_PolyPal(self,context)

        context.window_manager.modal_handler_add(self)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="VERT")
        if self.directCreate:
            bpy.ops.wm.tool_set_by_id(name="builtin.primitive_cube_add")
        return {'RUNNING_MODAL'}

    def register_handlers(self,args,context):
        self.draw_handle_leadingEdge = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_leadingEdge, args, "WINDOW", "POST_VIEW")
        self.draw_handle_Circle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_hilight_circle, args, "WINDOW", "POST_PIXEL")
        self.draw_event = context.window_manager.event_timer_add(0.1, window=context.window)

    def unregister_handlers(self,context):
        context.window_manager.event_timer_remove(self.draw_event)
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_leadingEdge, "WINDOW")
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_Circle, "WINDOW")

    def create_batch_leading_edge(self):
        points = []
        if len(self.vertices):
            points = (self.vertices[-1],self.vertices[0])
        self.shader_leadingEdge = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        self.batch = batch_for_shader(self.shader_leadingEdge, 'LINE_LOOP',{"pos": points})
    def draw_callback_leadingEdge(self,op,context):
        origLWidth = gpu.state.line_width_get()
        gpu.state.line_width_set(3)
        self.shader_leadingEdge.bind()
        self.shader_leadingEdge.uniform_float("color", (0.1, 0.75, 1, 1.0))
        self.batch.draw(self.shader_leadingEdge)
        gpu.state.line_width_set(origLWidth)

    def draw_callback_hilight_circle(self,op,context):
        if len(self.vertices):
            ScreenVertCoord = Vector(functions.convert_world_to_screen_coords(self.vertices[-1], context))
            origLWidth = gpu.state.line_width_get() 
            gpu.state.line_width_set(2)
            draw_circle_2d(ScreenVertCoord,(0.3, 1, 1, 1.0), 3, segments=8)
            gpu.state.line_width_set(origLWidth)


    def finish(self,context):
        self.unregister_handlers(context)
        return {"FINISHED"}


    def modal(self,context,event):
        prefs = context.preferences.addons[__package__].preferences
        if event.type in {'RIGHTMOUSE','ESC','RET','TAB'}:
            bpy.ops.object.mode_set(mode='OBJECT')
            context.active_object.display_type = 'TEXTURED'
            overlay.KillQOLHud()
            self.unregister_handlers(context)
            functions.finalise(self,context,objAvailable=True)
            bpy.ops.wm.tool_set_by_id(name=self.tool_id)
            context.area.tag_redraw()
            return {'FINISHED'}
        
        #CTRL MIDDLEMOUSE PRESS to send to QOL_OT_ModalVTXBevel
        if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS' and event.ctrl:

            if len(self.vertices) > 2:
                self.middleClick = True
                self.backup(self.vertices)
                self.initialMouseLoc = event.mouse_region_x, event.mouse_region_y
                if self.dotActive:
                    for handle in self.handler_handles:
                        try:
                            bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
                        except:
                            pass
                    self.dotActive = False
            else:
                self.report({'INFO'}, "Not enough vertices to bevel")
            return {'RUNNING_MODAL'}

        # MOUSEMOVE BEVEL
        if event.type == 'MOUSEMOVE' and self.middleClick and not event.alt:
            d1 = functions.convert_screen_to_world_coords(self.initialMouseLoc,context)
            d2 = functions.convert_screen_to_world_coords((event.mouse_region_x, event.mouse_region_y),context)
            distance = (d1-d2).length
            self.bevelRadius = round(distance,2)
            functions.mBevel(self,context)
            return {'RUNNING_MODAL'}
        
        # (F)illet or (C)hamfer        
        if event.type == 'C' and self.middleClick:
            self.bevelSegments = 1
            functions.mBevel(self,context)
            return {'RUNNING_MODAL'}
        if event.type == 'F' and self.middleClick:
            self.bevelSegments = 8
            functions.mBevel(self,context)
            return {'RUNNING_MODAL'}
        # SEGMENTS UP/DOWN 
        if event.type == 'WHEELUPMOUSE'and self.middleClick:
            self.bevelSegments += 1
            functions.mBevel(self,context)
            return {'RUNNING_MODAL'}
        if event.type == 'WHEELDOWNMOUSE'and self.middleClick:
            self.bevelSegments -= 1
            if self.bevelSegments < 1:
                self.bevelSegments = 1
            functions.mBevel(self,context)
            return {'RUNNING_MODAL'}
        
        # MIDDLEMOUSE RELEASE to finish bevel
        if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE' and self.middleClick:
            self.middleClick = False
            self.leftClick = False
            functions.rebuildListDataFromFaces(self,context)
            functions.redrawMesh(self,context)
            self.updateVecOverlays(context)
            self.dotActive = True
            return {'RUNNING_MODAL'}
        

        # ALT LEFT to delete a vertex
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and event.alt and not self.middleClick:
            self.backup(self.vertices)
            foundVertexIndex = self.proximityCheck(context,(event.mouse_region_x, event.mouse_region_y))
            if foundVertexIndex is not None:
                self.vertices.pop(foundVertexIndex)
                self.screenVtcs.pop(foundVertexIndex)
                functions.redrawMesh(self,context)
                self.updateVecOverlays(context)
            functions.rebuildMeshListData(self,context)
            # if self.objectViewMode:
            #     bpy.ops.object.mode_set(mode='OBJECT')

        #o to toggle object mode
        if event.type == 'O' and event.value == 'PRESS':
            self.objectViewMode = not self.objectViewMode
            return {'RUNNING_MODAL'}

        # LEFT CLICK
        try:
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and not event.alt and not event.shift and not self.middleClick:
                self.leftClick = True
                if len(self.vertices)>2:
                    self.backup(self.vertices.copy())
                mouse_loc = event.mouse_region_x, event.mouse_region_y
                #first check to see if we're clicking on a vertex
                foundVertex = False
                foundVertexIndex = self.proximityCheck(context,mouse_loc)
                if foundVertexIndex is not None:
                    foundVertex = True
                    self.screenVtcs = self.screenVtcs[foundVertexIndex+1:] + self.screenVtcs[:foundVertexIndex+1]
                    self.vertices = self.vertices[foundVertexIndex+1:] + self.vertices[:foundVertexIndex+1]
                    self.vertices.pop(-1)
                    self.screenVtcs.pop(-1)
                    self.updateVecOverlays(context)

                #if we're not clicking on a vertex, check to see if we're clicking on an edge
                if not foundVertex and len(self.vertices) >= 3:
                    try: #need to try in case of very rare unavoidable divide by zero error
                        min_dist = 20
                        nearest_edge = None
                        for i in range(len(self.screenVtcs)):
                            p1 = self.screenVtcs[i]
                            p2 = self.screenVtcs[(i+1)%len(self.screenVtcs)]
                            # Calculate the distance between the mouse click and the line defined by p1 and p2
                            dist = abs((p2[1]-p1[1])*mouse_loc[0] - (p2[0]-p1[0])*mouse_loc[1] + p2[0]*p1[1] - p2[1]*p1[0]) / math.sqrt((p2[1]-p1[1])**2 + (p2[0]-p1[0])**2)
                            # Calculate the dot product between the vector from p1 to the mouse click and the vector from p1 to p2
                            dot_product = (mouse_loc[0] - p1[0])*(p2[0] - p1[0]) + (mouse_loc[1] - p1[1])*(p2[1] - p1[1])
                            # Calculate the length of the vector from p1 to p2 squared
                            length_squared = (p2[0] - p1[0])**2 + (p2[1] - p1[1])**2
                            # Check if the projected point is within the line segment defined by p1 and p2
                            if dist < min_dist and 0 <= dot_product <= length_squared:
                                min_dist = dist
                                nearest_edge = (p1, p2)
                            if min_dist < 3:
                                insert_index = self.screenVtcs.index(nearest_edge[0]) + 1
                                self.vertices = self.vertices[insert_index:] + self.vertices[:insert_index]
                                self.screenVtcs = self.screenVtcs[insert_index:] + self.screenVtcs[:insert_index]
                                functions.redrawMesh(self,context)
                                self.updateVecOverlays(context)
                                self.leftClick = False
                                return {'RUNNING_MODAL'}
                    except:
                        pass
                
                vertex = None
                if len(self.vertices) > 0:
                    vertex = functions.get_mouse_3d_on_plane(self,event,context)
                else:
                    vertex = functions.get_mouse_3d_on_mesh(self,event,context)
                    # bpy.ops.wm.tool_set_by_id(name="builtin.poly_build")
                    bpy.ops.wm.tool_set_by_id(name="builtin.cursor")
                    

                self.vertices.append(vertex)
                self.screenVtcs.append(mouse_loc)
                functions.redrawMesh(self,context)
                self.updateVecOverlays(context)
                return {'RUNNING_MODAL'}
        except:
            pass





        #shift drag to draw vertices every .1 units
        if self.leftClick and event.type == 'MOUSEMOVE' and event.shift and not self.middleClick:
            mouse_loc = event.mouse_region_x, event.mouse_region_y
            vertex = functions.get_mouse_3d_on_plane(self,event,context)
            if (mouse_loc[0]-self.screenVtcs[-1][0])**2 + (mouse_loc[1]-self.screenVtcs[-1][1])**2 > 100:
                self.vertices.append(vertex)
                self.screenVtcs.append(mouse_loc)
                functions.redrawMesh(self,context)
            return {'RUNNING_MODAL'}

        # X for Grid Snapping
        if event.type == 'X' and event.value == 'PRESS':
            prefs.gridSnapping = not prefs.gridSnapping
            return {'RUNNING_MODAL'}

        # up arrow to change gridsize preference
        if event.type == 'UP_ARROW' and event.value == 'PRESS':
            sizeOptions = [0.1,0.25,0.5,0.75,1,1.25,1.5,2,5]
            prefs.gridSize = round(prefs.gridSize,2)
            sizeIndex = 0
            for i in range(len(sizeOptions)):
                if prefs.gridSize < sizeOptions[i]:
                    sizeIndex = i
                    break
            if sizeIndex == len(sizeOptions)-1:
                pass
            else:
                prefs.gridSize = sizeOptions[sizeIndex+1]
            print ("GridSize is now ..  ",prefs.gridSize)
                    
            return {'RUNNING_MODAL'}
        # down arrow to change gridsize preference
        if event.type == 'DOWN_ARROW' and event.value == 'PRESS':
            sizeOptions = [0.1,0.25,0.5,0.75,1,1.25,1.5,2,5]
            prefs.gridSize = round(prefs.gridSize,2)
            # get nearest size option
            sizeIndex = 0
            for i in range(len(sizeOptions)):
                if prefs.gridSize > sizeOptions[i]:
                    sizeIndex = i
            #now set it to the next size option
            if sizeIndex == 0:
                pass
            else:
                prefs.gridSize = sizeOptions[sizeIndex-1]
            print ("GridSize is now ..  ",prefs.gridSize)
            return {'RUNNING_MODAL'}


        #MOUSEMOVE
        try:
            if self.leftClick and event.type == 'MOUSEMOVE' and not event.shift and not self.middleClick:
                mouse_loc = event.mouse_region_x, event.mouse_region_y
                location = functions.get_mouse_3d_on_plane(self, event, context)
                if prefs.gridSnapping and functions.orthoCheck(context):
                    Sn = functions.getGridSize(context)
                    location = (round(location[0]/Sn)*Sn, round(location[1]/Sn)*Sn, round(location[2]/Sn)*Sn)
                    mouse_loc = functions.convert_world_to_screen_coords(location, context)
                if self.dotActive:
                    for handle in self.handler_handles:
                        try:
                            bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
                        except:
                            pass
                    self.dotActive = False

                self.vertices[-1] = location
                self.screenVtcs[-1] = mouse_loc
                functions.redrawMesh(self,context)
                self.updateVecOverlays(context)
                return {'RUNNING_MODAL'}
        except:
            pass

        #CTRL-Z funtionality
        if event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            if self.backup_manager.vertices_backups:
                index = len(self.backup_manager.vertices_backups) - self.backupIndex  
                if index > 0 and index < (len(self.backup_manager.vertices_backups)+1):
                    previous_vertices = self.backup_manager.vertices_backups[index]
                    self.vertices = previous_vertices
                    self.screenVtcs = [functions.convert_world_to_screen_coords(v, context) for v in self.vertices]
                    self.backupIndex += 1
                    self.undoProcess = True
                else:
                    # There are not enough backups to go back that many stages, so self.vertices remains unchanged
                    pass
            functions.redrawMesh(self,context)
            # self.updateVectorOverlays(context)
            return {'RUNNING_MODAL'}

        # Mousewheel up or down to reverse the order of the vertices
        if not self.leftClick and not self.middleClick and event.type in 'WHEELUPMOUSE' and event.alt:
            if len(self.vertices) > 0:
                self.vertices = self.vertices[1:] + self.vertices[:1]
                self.screenVtcs = self.screenVtcs[1:] + self.screenVtcs[:1]
                functions.redrawMesh(self,context)
                self.updateVecOverlays(context)
                return {'RUNNING_MODAL'}
        if not self.leftClick and not self.middleClick and event.type in 'WHEELDOWNMOUSE' and event.alt:
            if len(self.vertices) > 0:
                self.vertices = self.vertices[-1:] + self.vertices[:-1]
                self.screenVtcs = self.screenVtcs[-1:] + self.screenVtcs[:-1]
                functions.redrawMesh(self,context)
                self.updateVecOverlays(context)
                return {'RUNNING_MODAL'}
        
        # RELEASE
        if self.leftClick and event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.leftClick:
            functions.redrawMesh(self,context)
            self.updateVecOverlays(context)
            self.dotActive = True
            self.leftClick = False
        return {'PASS_THROUGH'}








    def updateVecOverlays(self,context):
        self.create_batch_leading_edge()

    def proximityCheck(self,context,mouse_loc):
        foundVertexIndex = None
        functions.rebuildMeshListData(self,context)
        for i in range(len(self.vertices)):
            if len (self.vertices) > 0:
                if (mouse_loc[0]-self.screenVtcs[i][0])**2 + (mouse_loc[1]-self.screenVtcs[i][1])**2 < self.drawFidelity:
                    foundVertexIndex = i
                    break
        return foundVertexIndex

    def backup(self,vertices):
        if self.undoProcess:
            self.undoProcess = False
            self.backup_manager.vertices_backups = []
        self.backup_manager.add_backup(vertices)
        self.backupIndex = 1








#-----------------------------------------------------------------------------------------------------------------
class BackupManager:
    def __init__(self):
        self.vertices_backups = []
    def add_backup(self, vertices):
        self.vertices_backups.append(vertices)
        if len(self.vertices_backups) > 30:
            self.vertices_backups.pop(0)


class QOL_OT_WeldSilhouette(Operator):
    """Weld the silhouette of multiple selected ngons"""
    bl_idname = "qol.weldsilhouette"
    bl_label = "QOL Weld Silhouette"
    bl_context = "mesh_edit"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        allInitialSelectedMeshes = []
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                #how many polygons are in the mesh
                if len(obj.data.polygons) == 1:
                    allInitialSelectedMeshes.append(obj.name)
        if len(allInitialSelectedMeshes) < 2:
            self.report({'WARNING'}, "Select at least 2 meshes")
            return {'CANCELLED'}
        
        meshA = bpy.data.objects[allInitialSelectedMeshes[0]]
        allInitialSelectedMeshes.pop(0)
        viewType = context.space_data.region_3d.view_perspective
        if viewType in {'PERSP', 'CAMERA'}:
            context.space_data.region_3d.view_perspective = 'ORTHO'
        context.space_data.region_3d.update()
        
        for meshB in allInitialSelectedMeshes:
            meshB = bpy.data.objects[meshB]
            bpy.ops.object.select_all(action='DESELECT')
            meshA.select_set(True)
            meshB.select_set(True)
            context.view_layer.objects.active = meshA

            context.space_data.region_3d.view_perspective = 'ORTHO'
            context.space_data.region_3d.update()
            #set view to ortho

            context.view_layer.objects.active = meshA
            bpy.ops.object.select_all(action='DESELECT')
            meshA.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            meshB.select_set(True)
            bpy.ops.mesh.knife_project(cut_through=True)
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = meshB
            meshB.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            meshA.select_set(True)
            bpy.ops.mesh.knife_project(cut_through=True)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.join()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.dissolve_limited(angle_limit=0.01,delimit={'SHARP'})
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            meshA = bpy.context.active_object
        context.space_data.region_3d.view_perspective = viewType
        context.space_data.region_3d.update()

        return {'FINISHED'}
    



class QOL_OT_PolyPalRectangle(Operator):
    """Directly draw a 2d rectangle"""
    bl_idname = "qol.polypalrectangle"
    bl_label = "QOL PolyPal Rectangle"
    bl_context = "mesh_edit"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        self.hit = Vector((0,0,0))
        self.normal = Vector((0,0,1))
        self.firstCorner = None
        self.secondCorner = None
        self.csr = None
        self.offset = 0.02      
        self.tool_id = context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname
        if context.space_data.type == 'VIEW_3D':

            overlay.draw_Hud_Rectangle(self,context)
            self.firstRun = True
            self.mousePressed = False
            context.window_manager.modal_handler_add(self)
            # bpy.ops.wm.tool_set_by_id(name="builtin.primitive_cube_add")
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}
        
    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE','ESC','RET','NUMPAD_ENTER','SPACE','TAB'}:
            bpy.ops.wm.tool_set_by_id(name="builtin.select", space_type='VIEW_3D')
            if context.active_object is not None:
                self.mesh = context.active_object.data
                functions.finalise(self,context,True)
            else:
                functions.finalise(self,context,False)
            # bpy.ops.wm.tool_set_by_id(name=self.tool_id)
            return {'FINISHED'}
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.firstCorner = functions.get_mouse_3d_on_mesh(self,event,context)

            #initiate the mesh
            if context.active_object is not None:
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            mesh = bpy.data.meshes.new("QOL_PolyRectangle")
            obj = bpy.data.objects.new("QOL_PolyRectangle", mesh)
            context.collection.objects.link(obj)
            context.view_layer.objects.active = obj
            bm = bmesh.new()
            for i in range(4):
                bm.verts.new((0,0,0))
            bm.verts.ensure_lookup_table()
            bm.faces.new((bm.verts[0],bm.verts[1],bm.verts[2],bm.verts[3]))
            bm.to_mesh(mesh)
            obj.select_set(True)
            self.mousePressed = True      
            return{'RUNNING_MODAL'}
        



        if event.type == 'MOUSEMOVE' and self.mousePressed:
            self.secondCorner = functions.get_mouse_3d_on_plane(self,event,context)

            cornerLocations3D = []
            topleft = Vector(self.firstCorner)
            bottomright = Vector(self.secondCorner)
            faceNormal = Vector(self.normal)
            #get the length vector from the first corner along the x axis of facenormal
            length_vector = faceNormal.cross(Vector((1,0,0)))
            if length_vector.length < 0.001:
                length_vector = faceNormal.cross(Vector((0,1,0)))
            length_vector.normalize()
            #get the width vector from the first corner along the y axis of facenormal
            width_vector = faceNormal.cross(length_vector)
            width_vector.normalize()
            #get the length and width of the rectangle
            length = (bottomright - topleft).dot(length_vector)
            width = (bottomright - topleft).dot(width_vector)
            #get the corner locations
            cornerLocations3D.append(topleft)
            cornerLocations3D.append(topleft + length_vector * length)
            cornerLocations3D.append(topleft + length_vector * length + width_vector * width)
            cornerLocations3D.append(topleft + width_vector * width)
            obj = context.active_object
            mesh = obj.data
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(mesh)
            bm.verts.ensure_lookup_table()
            for i in range(4):
                bm.verts[i].co = cornerLocations3D[i]
            bmesh.update_edit_mesh(mesh)
            bpy.ops.object.mode_set(mode='OBJECT')
            context.area.tag_redraw()
            return{'RUNNING_MODAL'}
        
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
            self.mousePressed = False
            context.area.tag_redraw()
            return{'RUNNING_MODAL'}
         
        return {'PASS_THROUGH'}



class QOL_OT_NGonCleaner(Operator):
    """Clean up extraneous edges to make a clean NGon"""
    bl_idname = "qol.ngoncleaner"
    bl_label = "Ngon Cleaner"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        originalMode = context.active_object.mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.dissolve_limited(angle_limit=0.0872665)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode=originalMode)
        return {'FINISHED'}
   

class QOL_OT_PolyPalCircle(Operator):
    """Directly draw a 2d circle"""
    bl_idname = "qol.polypalcircle"
    bl_label = "QOL PolyPal Circle"
    bl_context = "mesh_edit"
    bl_options = {'REGISTER', 'UNDO'}
    _running = False
    def __init__(self):
        self._running = True

    def invoke(self, context, event):
        self.hit = Vector((0,0,0))
        self.normal = Vector((0,0,1))
        self.csr = Vector((0,0,0))
        self.numSides = 32
        self.radius = 0.1
        self.mousePressed = False
        self.offset = 0.01
        self.tool_id = context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname
        overlay.draw_Hud_Circle(self,context)
        context.window_manager.modal_handler_add(self)
        # bpy.ops.wm.tool_set_by_id(name="builtin.primitive_cube_add")
        return {'RUNNING_MODAL'}



    def modal(self,context,event):
        if event.type in {'RIGHTMOUSE','ESC','RET','NUMPAD_ENTER','SPACE','TAB'}:
            bpy.ops.wm.tool_set_by_id(name="builtin.select", space_type='VIEW_3D')
            if context.active_object is not None:
                self.mesh = context.active_object.data
                functions.finalise(self,context,True)
            else:
                functions.finalise(self,context,False)
            
            return {'FINISHED'}
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.center = functions.get_mouse_3d_on_mesh(self,event,context)
            if context.active_object is not None:
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            mesh = bpy.data.meshes.new("QOL_PolyCircle")
            obj = bpy.data.objects.new("QOL_PolyCircle", mesh)
            context.collection.objects.link(obj)
            context.view_layer.objects.active = obj
            bm = bmesh.new()
            vertices = []
            #build a circle of vertices around the center point and self.normal as the normal vector and self.radius as the radius
            for i in range(self.numSides):
                angle = i * 2 * math.pi / self.numSides
                x = self.radius * math.cos(angle)
                y = self.radius * math.sin(angle)
                vertices.append(bm.verts.new((x,y,0)))
            for i in range(self.numSides):
                bm.edges.new((vertices[i],vertices[(i+1)%self.numSides]))
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            #create a face from the edges
            bm.faces.new(bm.verts)
            bm.to_mesh(mesh)
            obj.select_set(True)
            #move the object to the center point
            obj.location = self.hit
            #rotate the object to the normal
            obj.rotation_euler = self.normal.to_track_quat('Z','Y').to_euler()
            self.mousePressed = True      
            return{'RUNNING_MODAL'}
        
        if event.type == 'MOUSEMOVE' and self.mousePressed:
            self.radius = (functions.get_mouse_3d_on_mesh(self,event,context) - self.center).length
            obj = context.active_object
            mesh = obj.data
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(mesh)
            bm.verts.ensure_lookup_table()
            for i in range(self.numSides):
                angle = i * 2 * math.pi / self.numSides
                x = self.radius * math.cos(angle)
                y = self.radius * math.sin(angle)
                bm.verts[i].co = (x,y,0)
            bmesh.update_edit_mesh(mesh)
            bpy.ops.object.mode_set(mode='OBJECT')
            context.area.tag_redraw()
            return{'RUNNING_MODAL'}
        
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.mousePressed = False
            return{'RUNNING_MODAL'}


        return {'PASS_THROUGH'}




class QOL_CutProject(Operator):
    """Uses selected meshes to cut another mesh"""
    bl_idname = "qol.cutproject"
    bl_label = "QOL CutProject"
    bl_context = "mesh_edit"
    bl_options = {'REGISTER', 'UNDO'}
    deleteCutters: BoolProperty(default=True)   
    @classmethod
    def poll(cls, context):
        selected = context.selected_objects
        return (context.active_object is not None) and (len(selected) >= 2)

    def execute(self, context):
        allSelected = context.selected_objects
        if len(allSelected) < 2:
            self.report({'WARNING'}, "Select at least 2 objects")
            return {'CANCELLED'}
        obj = context.active_object
        for cutObj in allSelected:
            if cutObj != obj:
                cutObj.display_type = 'WIRE'
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        for cutObj in allSelected:
            if cutObj != obj:
                cutObj.select_set(True)
        bpy.ops.mesh.knife_project(cut_through=True)
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if self.deleteCutters:
            for cutObj in allSelected:
                if cutObj != obj:
                    cutObj.select_set(True)
            bpy.ops.object.delete(use_global=False)
        return {'FINISHED'}
    
class QOL_PT_PolyPalNPanel(Panel):
    bl_label = "QOL PolyPal"
    bl_idname = "QOL_PT_PolyPalPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "QOL"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        op = row.operator("qol.polypaldraw", icon_value=icons_dict["QOL_PolyPalDraw"].icon_id)
        op.directCreate = True
        layout.separator()
        gridFlow = layout.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=False)
        op = gridFlow.operator("qol.polypaldraw", text = "QOL_PolyPal Edit",icon_value=icons_dict["QOL_PolyPalDraw"].icon_id)
        op.directCreate = False
        gridFlow.operator("qol.polypalrectangle", icon='MESH_PLANE')
        gridFlow.operator("qol.polypalcircle", icon='MESH_CIRCLE')
        layout.separator()
        row = layout.row()
        row.operator("qol.cutproject", icon_value=icons_dict["QOL_CutProject"].icon_id)
        row = layout.row()
        row.operator("qol.ngoncleaner", icon='MOD_TRIANGULATE')
        row = layout.row()
        row.operator("qol.weldsilhouette",icon_value=icons_dict["QOL_CutProject"].icon_id)



