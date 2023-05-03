bl_info = \
    {
        "name" : "Simplicage",
        "author" : "Morelewd & Mustard",
        "version" : (1, 0, 9),
        "blender" : (3, 2, 0),
        "location" : "UI > Simplicage Pro",
        "description" : "Create a cage from the selection, with physics settings to deform the original mesh",
        "warning" : "", 
        "doc_url" : "https://simplicage.readthedocs.io/en/latest/",
        "category" : "Armature",
    }

import bpy
from bpy.props import PointerProperty
import mathutils
from mathutils import Matrix
from math import pi, exp , sqrt , sinh
import numpy as np
import bmesh
from bpy.types import Panel, Menu, AddonPreferences
from bl_operators.presets import AddPresetBase
import shutil
import os
import time

# ------------------------------------------------------------------------
#    Global Settings
# ------------------------------------------------------------------------

class Simplicage_CreateCageSettings(bpy.types.PropertyGroup):
    
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):
        return object.type == 'MESH'
    
    def update_mode_cage(self, context):
        if self.mode_cage == "BONE_CHAIN" or self.mode_cage == "VERTEX_GROUP":
            self.method = "SURFACE_DEFORM"
    
    # Users choices
    body: bpy.props.PointerProperty(name = "Mesh",
                        description = "Select the mesh where you want to create cages from",
                        type = bpy.types.Object,
                        poll = poll_mesh)
    
    mode_cage: bpy.props.EnumProperty(name = "Mode",
                        description = "Mode",
                        update = update_mode_cage,
                        items = (("BONE_SINGLE", "Single Bone", "Create a cage from selected bone(s)", "BONE_DATA", 0),
                        ("BONE_CHAIN", "Chain", "Create a unique cage from the selected bones.\nIf one bone is selected, mode will be switched to Single Bone", "LINK_BLEND", 1),
                        ("VERTEX_GROUP", "Vertex Group", "Create a cage from the vertex group", "GROUP_VERTEX", 2)))
    vertex_group: bpy.props.StringProperty(name = "Vertex Group")
    mode_phys: bpy.props.EnumProperty(name = "Mode",
                        description = "Physics mode",
                        default = "CLOTH",
                        items = (("NONE", "None", "Create a cage without applying physics", "SPHERE", 0),
                        ("CLOTH", "Cloth", "Create a physics-ready cage with Cloth physics", "PHYSICS", 1),
                        ("COLLISION", "Collision", "Create a collision box", "MOD_PHYSICS", 2)))
    advanced: bpy.props.BoolProperty(default = False,
                        name = "Advanced Settings",
                        description = "Enable various Advanced Settings")
    method: bpy.props.EnumProperty(name = "Method",
                        description = "The method with which the mesh will be deformed by the cage",
                        items = (("SURFACE_DEFORM", "Surface Deform", "Subsurface Deform will be parented with an Armature modifer","MOD_SUBSURF", 0),
                        ("MESH_DEFORM", "Mesh Deform", "Mesh Deform will be parented as a single object (ChildOf or standard parenting)", "MOD_MESHDEFORM", 1)))
    parenting_method: bpy.props.EnumProperty(name = "Parenting Method",
                        description = "Parenting method for the mesh when Mesh Deform is enabled",
                        items = (("BONE", "Bone parenting", "Bone parenting"),
                        ("CHILD_OF", "ChildOf", "ChildOf modifier")))
    filling_method: bpy.props.EnumProperty(name = "Filling Method",
                        description = "Filling method for closing the cage mesh",
                        default = "FILL_GRID_HOLE",
                        items = (("CONVEX_HULL", "Convex Hull", "Convex Hull"),
                        ("FILL_HOLE", "Fill Hole", "Fill Hole"),
                        ("FILL_GRID_HOLE", "Fill Grid Hole", "Fill Grid Hole"),
                        ("FILL_LAST", "Fill Last", "Fill Last")))
    pin_norm_method: bpy.props.EnumProperty(name = "Pin Group Normalization Method",
                        default = "SIGMOID",
                        items = (("NONE", "None", "None"),
                        ("LINEAR", "Linear", "Linear"),
                        ("X_SQUARE", "Square", "Square"),
                        ("SIGMOID", "Sigmoid", "Sigmoid"),
                        ("TANH", "Tanh", "Tanh"),
                        ("ARCSCH", "Arcsch", "Arcsch")))
    pin_use_proximity_data: bpy.props.BoolProperty(default = True,
                        description = "Use data from proximity of the generated cage to the original mesh, to improve the pin region",
                        name = "Use Proximity Data")
    pin_proximity_data_factor: bpy.props.FloatProperty(default = 5, min = 0.5, max = 20, step=25,
                        description = "Factor used to generate proximity data.\nHigher values will increase the pinned region near the closed mesh",
                        name = "Factor")
    threshold: bpy.props.FloatProperty(default = 0.95, min = 0., max = 1.,
                        description = "Ratio of selected bone deformed mesh to duplicate",
                        name = "Coverage")
    scale: bpy.props.FloatProperty(default = 1.05, min = 0.1, max = 2.,
                        description = "Scale the mesh after generation.\nWe advise a value >= 1.05 to ensure the cage enclose the mesh it's supposed to deform",
                        name = "Re-size Scale")
    remesh_seed: bpy.props.IntProperty(default = 0, min = 0, max = 10000,
                        description = "Remesher Seed, change this number if the cage generation fails or you want a different edge flow",
                        name = "Remesh seed")
    resolution: bpy.props.IntProperty(default = 300, min = 100,
                        description = "Resolution of the remesh",
                        name = "Resolution")
    voxel_volume: bpy.props.FloatProperty(default = 10., min = 0.001, max = 1000.,
                        description = "(Debug) Voxel Volume",
                        name = "(Debug) Voxel Volume")
    tanh_gain:bpy.props.FloatProperty(default = 1, min = 0.1, max = 100,
                        name = "Gain")
    tanh_min:bpy.props.FloatProperty(default = 0., min = 0., max = 1.,
                        name = "Min")
    arcsch_gain:bpy.props.FloatProperty(default = 1, min = 0.1, max = 100,
                        name = "Gain")
    arcsch_min:bpy.props.FloatProperty(default = 0., min = 0., max = 1.,
                        name = "Min")
    sigmoid_exp_fact:bpy.props.FloatProperty(default = 3., min = 0.1, max = 100,
                        name = "Gain")
    sigmoid_exp_shift:bpy.props.FloatProperty(default = .5, min = 0., max = 1.,
                        name = "Min")
    enable_smooth_corr: bpy.props.BoolProperty(default = True,
                        description = "Add a smooth correction modifier to the cage.\nThis might help to smooth instabilities",
                        name = "Smooth Correction")
    enable_smooth_corr_body: bpy.props.BoolProperty(default = False,
                        description = "Add a smooth correction modifier to the body.\nThis might help to smooth instabilities",
                        name = "Smooth Correction")
    remesh: bpy.props.BoolProperty(default = True,
                        name = "Remesh",
                        description = "Remesh the cage with Quadriflow Blender remesher")
    close_mesh: bpy.props.BoolProperty(default = True,
                        description = "Close the mesh with one of the methods listed",
                        name = "Close Cage Mesh")
    clean_selection: bpy.props.BoolProperty(default = False,
                        description = "Method to improve the selection of the mesh to duplicate",
                        name = "Clean Selection")
    clean_selection_threshold :bpy.props.FloatProperty(default = 1.5 , min = 0.5, max = 2.0,
                        description = "Clean Selection Threshold, Lower value means it will remove more geometry",
                        name = "Threshold")
    fix_influence: bpy.props.BoolProperty(default = True,
                        description = "Fix the influence group driving the surface/mesh deform influence",
                        name = "Fix Influence")
    fix_influence_gain:bpy.props.FloatProperty(default = 5., min = 1., max = 10.,
                        name = "Gain")
    
    def update_frame(self, context):
        
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type=="CLOTH":
                    mod.point_cache.frame_start = self.frame_start
                    mod.point_cache.frame_end = self.frame_end
                    
        return        
                
    # Bake settings
    frame_start: bpy.props.IntProperty(default = 1, min = 0, max = 1048574,
                        description = "Frame on which the simulation start",
                        name = "Start",
                        update = update_frame)
    frame_end: bpy.props.IntProperty(default = 250, min = 0, max = 1048574,
                        description = "Frame on which the simulation stops",
                        name = "End",
                        update = update_frame)
    
# ------------------------------------------------------------------------
#    Single Cage Settings
# ------------------------------------------------------------------------

class Simplicage_CageSettings(bpy.types.PropertyGroup):
    
    # Settings saved on the mesh
    bone: bpy.props.StringProperty(default = "")
    body: bpy.props.PointerProperty(type = bpy.types.Object)
    collision: bpy.props.BoolProperty(default=False)
    
    # Settings for the mesh
    def update_toggle_physics(self, context):
        
        cage = self.id_data
        
        for mod in cage.modifiers:
            if mod.type=="CLOTH":
                mod.show_viewport = self.toggle_physics
                mod.show_render = self.toggle_physics
        for mod in self.body.modifiers:
            if mod.type=="MESH_DEFORM":
                if mod.object == cage:
                    mod.show_viewport = self.toggle_physics
                    mod.show_render = self.toggle_physics
            if mod.type=="SURFACE_DEFORM":
                if mod.target == cage:
                    mod.show_viewport = self.toggle_physics
                    mod.show_render = self.toggle_physics
        
        return
                                
    toggle_physics: bpy.props.BoolProperty(default = True,
                        description = "Enable the Physics modifier for this cage",
                        name = "Toggle Physics",
                        update = update_toggle_physics)
    
    # Settings for the mesh
    def update_toggle_corrective(self, context):
        
        cage = self.id_data
        
        for mod in cage.modifiers:
            if mod.type=="CORRECTIVE_SMOOTH":
                mod.show_viewport = self.toggle_corrective
                mod.show_render = self.toggle_corrective
        for mod in self.body.modifiers:
            if mod.type=="CORRECTIVE_SMOOTH":
                if self.bone in mod.vertex_group:
                    mod.show_viewport = self.toggle_corrective
                    mod.show_render = self.toggle_corrective
        
        return
    
    toggle_corrective: bpy.props.BoolProperty(default = True,
                        description = "Enable Smooth Corrective modifiers for this cage",
                        name = "Toggle Smooth Corrective",
                        update = update_toggle_corrective)
                            
bpy.utils.register_class(Simplicage_CageSettings)
bpy.types.Object.Simplicage_CageSettings = bpy.props.PointerProperty(type = Simplicage_CageSettings)

# ------------------------------------------------------------------------
#    Addon settings (on addon panel)
# ------------------------------------------------------------------------

class Simplicage_AddonPrefs(bpy.types.AddonPreferences):
    
    bl_idname = bl_info["name"].lower()
    
    debug_mode: bpy.props.BoolProperty(default = False,
                        description = "Enable Debug mode",
                        name = "Debug mode")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "debug_mode")

# ------------------------------------------------------------------------
#    Cage creation operator
# ------------------------------------------------------------------------

class Simplicage_CreateCage(bpy.types.Operator):
    """Create a cage on bone selection.\nTo activate you need to be in pose mode and select at least one bone. Make sure to select the right body and its armature."""
    bl_idname = "physics.createcage"
    bl_label = "Cage generation"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    def main(context):
    
        list = []
        
        for num , ob in enumerate(bpy.context.selected_pose_bones):             
            list.append(ob.name)
        
        return list
    
    @classmethod
    def poll(cls, context):
            
        cage_settings = context.scene.Simplicage_CreateCageSettings
        
        if cage_settings.mode_cage != "VERTEX_GROUP":
            # Check if we are in pose mode, if the body mesh has been selected, and the pose bones selected are > 0
            if context.object != None:
                if context.object.mode == 'POSE' and cage_settings.body != None and bpy.context.selected_pose_bones != None:
                    if len(bpy.context.selected_pose_bones) > 0:
                        arma = bpy.context.active_pose_bone.id_data
                        body = cage_settings.body
                        for i in range(len(body.modifiers)):
                            if body.modifiers[i].type == "ARMATURE":
                                if body.modifiers[i].object == arma :
                                    return True;
                                else:
                                    return False;

        
        else:
            # Check that the body mesh has been selected, and that the vertex group is selected
            return cage_settings.body != None and cage_settings.vertex_group != ""
        
        return False
        
    def parent_bone(context, rig, bone_name, object):
        
        print('Parenting to the bone..')
        
        bpy.context.evaluated_depsgraph_get().update()
        bone = rig.pose.bones[bone_name]

        object.parent = rig
        object.parent_type = "BONE"
        object.parent_bone = bone_name

        vec = bone.head - bone.tail
        trans = mathutils.Matrix.Translation(vec)
        object.matrix_parent_inverse = bone.matrix.inverted() @ trans
        
        return    

    def parent_object(context,  body, object):
        
        print('Parenting to the bone..')
#        
        bpy.context.evaluated_depsgraph_get().update()
        
        if object.parent :
           bpy.ops.object.mode_set(mode = 'OBJECT')
           bpy.ops.object.select_all(action='DESELECT')
           object.select_set(True)
           bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
           
        object.parent = body
        object.parent_type = "OBJECT"
        object.matrix_parent_inverse = body.matrix_world.inverted()
        return
    
    def cleanThings(self, body, bone, cage_settings, chainName):
        
        print('Cleaning previous cages modifiers and vertex groups..')
        
        cages = [x for x in bpy.data.objects if x.Simplicage_CageSettings.bone == bone]
        cages_bones = [x.Simplicage_CageSettings.bone + "_SimplicageBind" for x in bpy.data.objects if x.Simplicage_CageSettings.bone != ""]
        
        # Remove old modifiers
        for modifier in [x for x in cage_settings.body.modifiers if x.type == "SURFACE_DEFORM"]:
            if modifier.target in cages or modifier.target == None:
                body.modifiers.remove(modifier)
        for modifier in [x for x in cage_settings.body.modifiers if x.type == "MESH_DEFORM"]:
            if modifier.object in cages or modifier.object == None:
                body.modifiers.remove(modifier)
        for modifier in [x for x in cage_settings.body.modifiers if x.type == "CORRECTIVE_SMOOTH"]:
            if bone in modifier.vertex_group:
                body.modifiers.remove(modifier)
        
        # Clean selection in edit mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = body
        
        # Remove old chain vertex group
        if chainName:
            chaing = body.vertex_groups.get(chainName)
            if chaing is not None:
                body.vertex_groups.remove(chaing)
        # Remove old bind groups
        for group in body.vertex_groups:
            name = group.name.replace("Chain-" , "")
            name2 = name.replace("_SimplicageBind" , "")
            if cage_settings.mode_cage == "BONE_CHAIN":
                if "_SimplicageBind" in group.name and bone == name2 :
                    boneg = body.vertex_groups.get(group.name)
                    if boneg is not None:
                        print("Pruning unused vertex group: " + name , cages_bones ,bone , name2)
                        body.vertex_groups.remove(boneg)
            else:
                  if "_SimplicageBind" in group.name and bone == name2 :
                    boneg = body.vertex_groups.get(group.name)
                    if boneg is not None:
                        print("Pruning unused vertex group single: " + group.name , cages_bones , bone , name2)
                        body.vertex_groups.remove(boneg)

        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        return
    
    def selectVerts(self, body, bone, cage_settings, chainName):
        
        print('Selecting the vertices for the cage.. ,' ,  bone)
        
        if chainName:
            if cage_settings.mode_cage == "BONE_CHAIN" and cage_settings.mode_phys != "COLLISION":
                 if not chainName in [g.name for g in body.vertex_groups]:
                    chain_group = body.vertex_groups.new(name = chainName )
                 else:
                    chain_group = body.vertex_groups[chainName]
                 chain_group_index = body.vertex_groups[chain_group.name].index
        
        body_group_names = [g.name for g in body.vertex_groups]
        body_verts = body.data.vertices
        i = 0
        if bone in body_group_names:
            gidx = body.vertex_groups[bone].index
            

        else:
            self.report({'ERROR'}, 'The bone \'' + bone + '\' has no associated vertex group.')
            return False
        
        # Select the vertices
        bone_verts = [v for v in body_verts if gidx in [g.group for g in v.groups]]
        for v in bone_verts:
            for g in v.groups:
                if g.group == gidx: 
                    if g.weight >  ( 1.0 - cage_settings.threshold):
                        if chainName and cage_settings.mode_cage == "BONE_CHAIN" and cage_settings.mode_phys != "COLLISION":
                            body.vertex_groups[chain_group_index].add([v.index], g.weight , 'ADD')
                        v.select = True
                        i += 1
        
        if i < 1:
            self.report({'ERROR'}, 'With this coverage setting, no vertex was selected for \'' + bone + '\'. Lower the value and try again.')
            return False
        else:
            return True
                    
    def duplicateMesh(self, body, armature, bone, cage_settings):
        
        debug_mode = bpy.context.preferences.addons[bl_info["name"].lower()].preferences.debug_mode
        
        print('Duplicating the body mesh..')
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.duplicate_move(MESH_OT_duplicate={"mode":1}, TRANSFORM_OT_translate={"value":(0, 0, 0),  "orient_type":'LOCAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'LOCAL', "constraint_axis":(False, False, False), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":0.0200863, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False,"release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        cage = bpy.context.selected_objects[0]
        bpy.context.view_layer.objects.active = cage
        cage.visible_camera = False
        cage.visible_diffuse = False
        cage.visible_glossy = False
        cage.visible_transmission = False
        cage.visible_volume_scatter = False
        cage.visible_shadow = False


        cage.display_type = 'WIRE'
        cage.hide_render = True
        
        # Clean stuffs
        for modifier in [x for x in cage.modifiers ]:
            cage.modifiers.remove(modifier)
        cage.data.materials.clear()
        cage.vertex_groups.clear()
        if cage.data.shape_keys != None:
            if len(cage.data.shape_keys.key_blocks) > 0:
                bpy.ops.object.convert(target='MESH')
                cage.shape_key_clear()
        
        if cage_settings.method == "SURFACE_DEFORM" and armature != None:
            modif = cage.modifiers.new(name = "Armature", type = 'ARMATURE')            
            modif.object = armature
            modif.use_deform_preserve_volume = True
        
        cage.name = 'cage-' + bone
        
        cage.Simplicage_CageSettings.bone = bone
        cage.Simplicage_CageSettings.body = body
        cage.Simplicage_CageSettings.collision = cage_settings.mode_phys == "COLLISION"
        
        return cage
    
    def cleanSelection(self, cage , cage_settings):
        
        print('Cleaning the mesh selection..')
        threshold = cage_settings.clean_selection_threshold
        bpy.ops.object.editmode_toggle()
        bm = bmesh.from_edit_mesh(cage.data)
        bm.select_mode |= {'VERT'} 
        bm.verts.sort(key=lambda v: v.index)
        keep_running = True      
        while keep_running:
              bm.verts.ensure_lookup_table()
              count = 0              
              for v in bm.verts:
                if len(v.link_edges) < 2:
                    bm.verts.remove(v)
                    continue                   
                if len(v.link_edges) < 3:
                    angle = v.calc_edge_angle()
                    if angle > threshold:
                        bm.verts.remove(v)
                        count += 1 
                        bmesh.update_edit_mesh(cage.data) 
                        bm.verts.ensure_lookup_table()
              if count == 0:
                  keep_running = False
        bpy.ops.object.editmode_toggle()
        
        return
    
    def find_edge_rings(self , loop):
        
        i=0
        first_loop=loop
        while i < 1000 : 
            # Jump to adjacent face and walk two edges forward
            loop = loop.link_loop_radial_next.link_loop_next
            if(loop.edge.is_manifold != True):
                loop.edge.select = True
            i += 1
            # If radial loop links back here, we're boundary, thus done        
            if loop == first_loop:
                break
        
        return
    
    def closeObject(self, cage, cage_settings):
        
        print('Closing the cage..')
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.delete_loose(use_faces = True)
        bpy.ops.mesh.vert_connect_concave()
        bpy.ops.mesh.vert_connect_nonplanar()
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        if cage_settings.filling_method == "FILL_GRID_HOLE":
            bm = bmesh.from_edit_mesh(cage.data)
            manifold2 = True
            i = 0
            iter = 300
            while manifold2 and i < iter:
                i += 1
                manifold = False         
                for e in bm.edges: 
                    if e.is_manifold != True:
                        e.select = True
                        self.find_edge_rings(e.link_loops[0])
                        bmesh.update_edit_mesh(cage.data)
                        manifold = True
                        break
                    bm.edges.ensure_lookup_table()
                    if e == bm.edges[-1] and manifold == False:
                        manifold2 = False
                if manifold:        
                    bpy.ops.mesh.fill_grid(span=2)
                    bm.select_flush(True)
                    bm.select_flush_mode()
                    bm.edges.ensure_lookup_table()
                    bpy.ops.mesh.select_all(action = 'DESELECT')
                bmesh.update_edit_mesh(cage.data)
            bpy.ops.object.editmode_toggle()
            
        if cage_settings.filling_method == "FILL_HOLE":
            bm = bmesh.from_edit_mesh(cage.data)
            manifold2 = True
            i = 0
            iter = 300
            while manifold2 and i < iter:
                i += 1
                manifold = False         
                for e in bm.edges: 
                    if e.is_manifold != True:
                        e.select = True
                        self.find_edge_rings(e.link_loops[0])
                        bmesh.update_edit_mesh(cage.data)
                        manifold = True
                        break
                    bm.edges.ensure_lookup_table()
                    if e == bm.edges[-1] and manifold == False:
                        manifold2 = False
                if manifold:        
                    bpy.ops.mesh.fill()
                    bm.select_flush(True)
                    bm.select_flush_mode()
                    bm.edges.ensure_lookup_table()
                    bpy.ops.mesh.select_all(action = 'DESELECT')
                bmesh.update_edit_mesh(cage.data)
            bpy.ops.object.editmode_toggle()
        
        if cage_settings.filling_method == "CONVEX_HULL":
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.convex_hull(delete_unused=True, use_existing_faces=True, make_holes=False)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.object.editmode_toggle()
        
        if cage_settings.filling_method == "FILL_LAST": 
            self.remeshCage(cage, cage_settings)
        
        return True
    
    def remeshCage(self, cage, cage_settings):
        
        print('Remeshing the cage..')
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.vert_connect_concave()       
        bpy.ops.object.mode_set(mode = 'OBJECT')
        mod = cage.modifiers.new(name = "remesh-cage", type = 'REMESH')
        mod.mode = 'SMOOTH'
        mod.octree_depth = 5

        mod.scale = .5
        mod.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier="remesh-cage")
 
        return
    
    def remeshObject(self, cage, cage_settings):
        
        print('Remeshing the cage..')
        
        # Number of attempts made with the remesher
        iter = 5
        debug_mode = bpy.context.preferences.addons[bl_info["name"].lower()].preferences.debug_mode
        initial_resolution = cage_settings.resolution

        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        count1 = len(cage.data.vertices)
        count2 = count1
        i = 0
        bm = bmesh.new()
        bm.from_mesh( cage.data )
        volume = float( bm.calc_volume() )
        if volume < 0.003:
            volume = 0.003
        
        # Remesh the cage
        cage.data.remesh_mode = 'QUAD'

        with bpy.context.temp_override(object=cage):             
                
             bpy.ops.object.quadriflow_remesh(
                                target_faces = cage_settings.resolution,
                                smooth_normals = True,
                                use_mesh_symmetry = False,
                                use_preserve_boundary = True,
                                mode='FACES',
                                seed = cage_settings.remesh_seed)
            
             count2 = len(cage.data.vertices)
             
             if count1 == count2:
                print('remesh failed' , volume , cage_settings.resolution , cage_settings.voxel_volume);
                
                bpy.context.object.data.remesh_mode = 'VOXEL'
                if debug_mode:
                    bpy.context.object.data.remesh_voxel_size = cage_settings.voxel_volume * 10 
                else:
                    bpy.context.object.data.remesh_voxel_size = volume

                bpy.ops.object.voxel_remesh()
                count3 = len(cage.data.vertices)
                bpy.ops.object.mode_set(mode = 'EDIT')
                bpy.ops.mesh.select_all(action = 'SELECT')
                bpy.ops.mesh.decimate(ratio=0.5, use_vertex_group=False, vertex_group_factor=1, use_symmetry=False)
                bpy.ops.object.mode_set(mode = 'OBJECT')
                cage.data.remesh_mode = 'QUAD'
                remeshed = bpy.ops.object.quadriflow_remesh(
                                target_faces = cage_settings.resolution,
                                smooth_normals = True,
                                use_mesh_symmetry = False,
                                use_preserve_boundary = True,
                                mode='FACES',
                                seed = cage_settings.remesh_seed)
                print('remeshed value' , remeshed)

        

        cage_settings.resolution = initial_resolution
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.vert_connect_concave()
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        return True
    
    def generateProximityData(self, cage, body, cage_settings):
        
        print('Generating proximity data from the body to the cage..')
        
        vg = cage.vertex_groups.new(name = "Proximity data")
        for v in cage.data.vertices:
            vg.add([v.index], .0, 'REPLACE')
        
        modifier = cage.modifiers.new(name = "Proximity data", type = 'VERTEX_WEIGHT_PROXIMITY')
        while cage.modifiers.find(modifier.name) > 0:
            with bpy.context.temp_override(object=cage):
                bpy.ops.object.modifier_move_up(modifier = modifier.name)
        
        modifier.vertex_group = vg.name
        modifier.target = body
        modifier.proximity_mode = "GEOMETRY"
        modifier.proximity_geometry = {"FACE"}
        modifier.min_dist = 0.0
        modifier.max_dist = (cage_settings.pin_proximity_data_factor / 100)
        modifier.falloff_type = "SMOOTH"
        modifier.invert_falloff = False
        
        bpy.ops.object.modifier_apply(modifier = modifier.name)
        
        # Smooth in weight paint mode
        bpy.ops.object.select_all(action='DESELECT')
        cage.select_set(True)
        bpy.ops.paint.weight_paint_toggle()
        bpy.ops.object.vertex_group_smooth(factor=0.5, repeat=10, expand=0.8)
        bpy.ops.object.vertex_group_smooth(factor=0.5, repeat=1, expand=0.)
        bpy.ops.paint.weight_paint_toggle()
        
        return
    
    def scaleObject(self, cage, cage_settings):
        
        print('Scaling the mesh..')
        
        bpy.ops.object.origin_set(type = 'ORIGIN_GEOMETRY', center = 'BOUNDS')   
        cage.scale = cage.scale * cage_settings.scale
        
        return
            
    def transferData(self, cage, body):
        
        print('Transfering data from the body to the cage..')
        
        modifier = cage.modifiers.new(name = "Data Transfer-cage", type = 'DATA_TRANSFER')
        modifier.object = body
        modifier.use_vert_data = True
        modifier.data_types_verts = {'VGROUP_WEIGHTS'}
        bpy.ops.object.datalayout_transfer(modifier = modifier.name)
        with bpy.context.temp_override(object=cage):
            while cage.modifiers.find(modifier.name) > 0:
                with bpy.context.temp_override(object=cage):
                    bpy.ops.object.modifier_move_up(modifier = modifier.name)
            bpy.ops.object.modifier_apply(modifier = modifier.name)
        
        return
    
    def arcsch( self, x ,cage_settings):
        
        val = 1.0 - np.tanh(x/cage_settings.arcsch_gain) + cage_settings.arcsch_min
        return val
    
    def mapRange(self , x):
        
        return x* ((4+4)/(1-0))-4
    
    def normalizeWeights(self, x, cage_settings):
        
        pin_norm_method = cage_settings.pin_norm_method

        if pin_norm_method == "SIGMOID":
            
            xprime = self.mapRange(x)
            val = 1 / (1 + exp(-cage_settings.sigmoid_exp_fact*(xprime-(cage_settings.sigmoid_exp_shift*5))))
            return val
        elif pin_norm_method == "SQUARE":
            val = x**2.
            return val
        elif pin_norm_method == "TANH":
            if x and x > cage_settings.tanh_min:
                val = np.tanh(x*cage_settings.tanh_gain)
                return val
            else:
                val = cage_settings.tanh_min
                return val
        elif pin_norm_method == "ARCSCH":
            val = self.arcsch(x ,cage_settings)
            return val
        elif pin_norm_method == "LINEAR":
            return x
        else:
            return 0.

    def setWeights(self, bones, cage, body, cage_settings , activeBone):
        
        print('Settings weights..')
        
        if not "Pin" in [g.name for g in cage.vertex_groups]:
                pin_group = cage.vertex_groups.new(name = "Pin")
        else:
                pin_group = cage.vertex_groups["Pin"]
                
        dst_group_index = cage.vertex_groups[pin_group.name].index
        cage_verts = cage.data.vertices
        
        bone_indices = []
        for bone in bones:
                try:
                    bone_indices.append(cage.vertex_groups[bone].index)
                except:
                    continue;
                
        bone_verts = []
        for index in bone_indices:
            for v in [v for v in cage_verts if index in [g.group for g in v.groups]]:
                if not v in bone_verts:
                    bone_verts.append(v)
        if cage_settings.pin_use_proximity_data and cage_settings.close_mesh:
            src_group_index_proximity = cage.vertex_groups["Proximity data"].index
            for v in [v for v in cage_verts if src_group_index_proximity in [g.group for g in v.groups]]:
                if not v in bone_verts:
                    bone_verts.append(v)
          
        for v in bone_verts:
            
            w = 0.
            
            if cage_settings.pin_use_proximity_data and cage_settings.close_mesh:
            
                w2 = 0.
            
                for g in v.groups:
                    w = g.weight if g.group in bone_indices and g.weight > w else w
                    w2 = g.weight if g.group == src_group_index_proximity else w2
                
                cage.vertex_groups[dst_group_index].add([v.index], min(self.normalizeWeights(1.0 - w, cage_settings) + w2,1.), 'REPLACE')
            
            else:
                
                for g in v.groups:
                    w = g.weight if g.group in bone_indices and g.weight > w else w
                    
                cage.vertex_groups[dst_group_index].add([v.index], self.normalizeWeights(1.0 - w, cage_settings), 'REPLACE')
        
        bpy.ops.object.select_all(action='DESELECT')
        cage.select_set(True)
        bpy.ops.paint.weight_paint_toggle()
        
        bpy.ops.object.vertex_group_smooth(factor=0.5, repeat=8, expand=-0.12)
        bpy.ops.paint.weight_paint_toggle()
        
        return
    
    def setWeightsSingle(self, bone, cage, body, cage_settings):
        
        print('Settings weights..')
        
        pin_group = cage.vertex_groups.new(name = "Pin")
                
        dst_group_index = cage.vertex_groups[pin_group.name].index
        cage_verts = cage.data.vertices       
        src_group_index = cage.vertex_groups[bone].index
        if cage_settings.pin_use_proximity_data and cage_settings.close_mesh:
            src_group_index_proximity = cage.vertex_groups["Proximity data"].index
            bone_verts = [v for v in cage_verts if src_group_index in [g.group for g in v.groups] or src_group_index_proximity in [g.group for g in v.groups]]
        else:
            bone_verts = [v for v in cage_verts if src_group_index in [g.group for g in v.groups]]
        
        for v in bone_verts:
            
            if cage_settings.pin_use_proximity_data and cage_settings.close_mesh:
                
                w = 0.
                w2 = 0.
            
                for g in v.groups:
                    w = g.weight if g.group == src_group_index else w
                    w2 = g.weight if g.group == src_group_index_proximity else w2
                
                cage.vertex_groups[dst_group_index].add([v.index], self.normalizeWeights(1.0 - w, cage_settings) + w2, 'REPLACE')
            
            else:
                for g in v.groups:
                    if g.group == src_group_index:
                        w = g.weight
                        cage.vertex_groups[dst_group_index].add([v.index], self.normalizeWeights(1.0 - w, cage_settings), 'REPLACE')

        return
    
    # Make a copy of the vertex group that is responsible for that bone
    # and crank up the weight so the cage can affect all of the area
    def modifyVertexGroupCopy(self, bone, cage, body, cage_settings):
        
        print('Fixing body influence vertex group..')
        
        try:
            body.vertex_groups[bone + '_SimplicageBind']
        except:
            body.vertex_groups.active_index = body.vertex_groups[bone].index
            with bpy.context.temp_override(object=body):
                bpy.ops.object.vertex_group_copy()
                body.vertex_groups.active.name = bone + '_SimplicageBind'
       
        try:
            idx = body.vertex_groups[bone + '_SimplicageBind'].index
            body.vertex_groups.active_index = idx
            bpy.ops.object.select_all(action='DESELECT')
            body.select_set(True)
            bpy.ops.paint.weight_paint_toggle()
            print('Setting up  weight ', bone)
            with bpy.context.temp_override(object=body):
                bpy.ops.object.vertex_group_levels(group_select_mode='ACTIVE', offset=-0.04, gain=cage_settings.fix_influence_gain)
                bpy.ops.paint.weight_paint_toggle()
        except:
            print('modifyVertexGroupCopy: Can\'t find the vertex group copy')
        
        return
    
    def bindCage(self, cage, body, armature, bone, cage_settings , chainName):
        
        print('Binding the cages..')
        
        # Add the mesh deform modifier  
        modifier = body.modifiers.new(name = "Cage Physics " + bone, type = cage_settings.method)
        if cage_settings.method == "MESH_DEFORM":
            modifier.object = cage
            modifier.use_dynamic_bind = False
        else:
            modifier.target = cage

        if cage_settings.mode_cage == "BONE_CHAIN":
            modifier.vertex_group = chainName

        else:
            try:
                body.vertex_groups[bone + "_SimplicageBind"]
                modifier.vertex_group = bone + "_SimplicageBind"
            except:
                print('bind simplicage group not found' , bone + "_SimplicageBind" )
                modifier.vertex_group = bone

        if cage_settings.mode_cage == "BONE_CHAIN" and cage_settings.fix_influence:
            modifier.vertex_group = chainName + "_SimplicageBind"

        # Move modifier after the last armature modifier
        arm_mod_id = 0
        for i in range(len(body.modifiers)):
            if body.modifiers[i].type == "ARMATURE":
                arm_mod_id = i
        while body.modifiers.find(modifier.name) > arm_mod_id + 1:
            with bpy.context.temp_override(object=body):
                bpy.ops.object.modifier_move_up(modifier = modifier.name)
        
        # Bind the cage to the mesh
        if cage_settings.method == "MESH_DEFORM":
            bpy.ops.object.meshdeform_bind({"object" : body}, modifier = modifier.name)
            
            # Parenting
            if cage_settings.parenting_method == 'BONE':
                self.parent_bone(armature, bone, cage)
            
            # Parenting with ChildOf
            else:
                constraint = cage.constraints.new('CHILD_OF')
                constraint.target = armature
                constraint.subtarget = bone

        else:
            with bpy.context.temp_override(object=body):
                if cage_settings.mode_cage == 'VERTEX_GROUP':
                    self.parent_object(body, cage)
                bpy.ops.object.surfacedeform_bind( modifier = modifier.name)
                if not modifier.is_bound:
                    bpy.ops.object.surfacedeform_bind( modifier = modifier.name)
                        
                    if not modifier.is_bound:
                        

                            bpy.ops.object.select_all(action='DESELECT') 
                            bpy.context.view_layer.objects.active = cage
                            cage.select_set(True)
                            bpy.ops.object.editmode_toggle()
                            bpy.ops.mesh.select_all(action='SELECT')
                            bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
                            bpy.ops.object.editmode_toggle()

                            bpy.ops.object.select_all(action='DESELECT') 
                            bpy.context.view_layer.objects.active = body
                            body.select_set(True)

                            bpy.ops.object.surfacedeform_bind( modifier = modifier.name)                    
                    if not modifier.is_bound:
                        return False
        
        if cage_settings.enable_smooth_corr_body:
            
            print('Adding Smooth Correction to the body..')
            nme = "Cage Physics Smooth " + bone
            found = body.modifiers.find(nme)
            if found == -1:
                smooth_modifier = body.modifiers.new(name = "Cage Physics Smooth " + bone, type = "CORRECTIVE_SMOOTH")
                smooth_modifier.vertex_group = bone
                
                # Move modifier after the last armature modifier
                cg_mod_id = 0
                for i in range(len(body.modifiers)):
                    if body.modifiers[i].type == cage_settings.method:
                        cg_mod_id = i
                while body.modifiers.find(smooth_modifier.name) > cg_mod_id + 1:
                    with bpy.context.temp_override(object=body):
                        bpy.ops.object.modifier_move_up(modifier = smooth_modifier.name)
            
        return True
               
    def addClothPhyiscs(self, cage, body, bone, cage_settings, context):
        
        print('Adding Cloth modifier to the cage..')
        
        # Cloth modifier
        # Remove any previous cloth modifier
        for modifier in cage.modifiers:
            if modifier.type == "CLOTH":
                body.modifiers.remove(cage.modifiers.get(modifier.name))
        
        modifier = cage.modifiers.new(name = "Cage Physics", type='CLOTH')
        
        # Universal settings
        modifier.settings.vertex_group_mass = "Pin"
        modifier.settings.pin_stiffness = 50.
        modifier.settings.use_dynamic_mesh = False
        # Set the initial/end frame based on the global cache settings
        modifier.point_cache.frame_start = cage_settings.frame_start
        modifier.point_cache.frame_end = cage_settings.frame_end

        return modifier                
    
    
    def orderModifiers(self, modifier, cage):
        
        print('Ordering the modifiers correctly..')
        
        # Move modifier after the last armature modifier
        arm_mod_id = 0
        for i in range(len(cage.modifiers)):
            if cage.modifiers[i].type == "ARMATURE":
                arm_mod_id = i
        while cage.modifiers.find(modifier.name) > arm_mod_id + 1:
            with bpy.context.temp_override(object=body):
                bpy.ops.object.modifier_move_up(modifier = modifier.name)
        
        return
    
    def addSmoothCorrModifier(self, cage, cage_settings):
        
        print('Adding Smooth Correction to the cage..')
        
        modifier = cage.modifiers.new(name = "Cage Physics Smooth", type='CORRECTIVE_SMOOTH')
        cloth_mod_id = 0
        for i in range(len(cage.modifiers)):
            if cage.modifiers[i].type == "CLOTH":
                cloth_mod_id = i
        while cage.modifiers.find(modifier.name) > cloth_mod_id + 1:
            with bpy.context.temp_override(object=body):
                bpy.ops.object.modifier_move_up(modifier = modifier.name)
        
        return
    
    def loadPreset(self):
        
        print('Loading selected preset..')
        
        if bpy.types.SIMPLICAGE_MT_display_presets.bl_label != 'Presets':
             filename = bpy.types.SIMPLICAGE_MT_display_presets.bl_label.replace(" ", "_") + '.py'
             filept =  os.path.join(bpy.utils.script_path_user(), 'presets', 'simplicage', filename )
             bpy.ops.script.execute_presetperso(filepath=filept, menu_idname="simplicage_display_presets")
        
        return
    
    def addCollisionModifier(self , cage):
        
        print('Adding collision modifier..')
        
        modif_coll = cage.modifiers.new(name = "Collision Box", type = 'COLLISION')     
        cage.collision.thickness_outer = 0.001
        cage.collision.thickness_inner = 0.01
        
        return
    
    def finalCleanup(self, cage, cage_settings):
        
        # Functions thanks to Demeter Dzadik (Easy Weight addon: https://gitlab.com/blender/easy_weight)
        
        debug_mode = bpy.context.preferences.addons[bl_info["name"].lower()].preferences.debug_mode
        
        def get_deforming_armature(mesh_ob):
            for m in mesh_ob.modifiers:
                if m.type=='ARMATURE':
                    return m.object

        def delete_vgroups(mesh_ob, vgroups):
            for vg in vgroups:
                mesh_ob.vertex_groups.remove(vg)

        def get_deforming_vgroups(mesh_ob):
            arm_ob = get_deforming_armature(mesh_ob)
            if arm_ob == None:
                return []
            all_vgroups = mesh_ob.vertex_groups
            deforming_vgroups = []
            for b in arm_ob.data.bones:
                if b.name in all_vgroups and b.use_deform:
                    deforming_vgroups.append(all_vgroups[b.name])
            return deforming_vgroups

        def get_empty_deforming_vgroups(mesh_ob):
            deforming_vgroups = get_deforming_vgroups(mesh_ob)
            empty_deforming_groups = [vg for vg in deforming_vgroups if not vgroup_has_weight(mesh_ob, vg)]
            
            if not 'MIRROR' in [m.type for m in mesh_ob.modifiers]:
                return empty_deforming_groups

            for empty_vg in empty_deforming_groups[:]:
                opposite_vg = mesh_ob.vertex_groups.get(flip_name(empty_vg.name))
                if not opposite_vg:
                    continue
                if opposite_vg not in empty_deforming_groups:
                    empty_deforming_groups.remove(empty_vg)
            
            return empty_deforming_groups

        def get_non_deforming_vgroups(mesh_ob):
            all_vgroups = mesh_ob.vertex_groups
            deforming_vgroups = get_deforming_vgroups(mesh_ob)
            return set(all_vgroups) - set(deforming_vgroups)

        def get_vgroup_weight_on_vert(vgroup, vert_idx):
            try:
                w = vgroup.weight(vert_idx)
                return w
            except RuntimeError:
                return -1

        def vgroup_has_weight(mesh_ob, vgroup):
            for i in range(0, len(mesh_ob.data.vertices)):
                if get_vgroup_weight_on_vert(vgroup, i) > 0:
                    return True
            return False
        
        def get_referenced_vgroups(mesh_ob: bpy.types.Object, py_ob: object):
            """Return a list of vertex groups directly referenced by the object's attributes."""
            referenced_vgroups = []
            for member in dir(py_ob):
                value = getattr(py_ob, member)
                if type(value) != str:
                    continue
                vg = mesh_ob.vertex_groups.get(value)
                if vg:
                    referenced_vgroups.append(vg)
            return referenced_vgroups

        def get_shape_key_mask_vgroups(mesh_ob):
            mask_vgroups = []
            if not mesh_ob.data.shape_keys:
                return mask_vgroups
            for sk in mesh_ob.data.shape_keys.key_blocks:
                vg = mesh_ob.vertex_groups.get(sk.vertex_group)
                if vg and vg.name not in mask_vgroups:
                    mask_vgroups.append(vg)
            return mask_vgroups

        
        def delete_unused_vgroups(mesh_ob):
            non_deform_vgroups = get_non_deforming_vgroups(mesh_ob)
            used_vgroups = []

            # Modifiers
            for m in mesh_ob.modifiers:
                used_vgroups.extend(get_referenced_vgroups(mesh_ob, m))
                # Physics settings
                if hasattr(m, 'settings'):
                    used_vgroups.extend(get_referenced_vgroups(mesh_ob, m.settings))

            # Shape Keys
            used_vgroups.extend(get_shape_key_mask_vgroups(mesh_ob))

            groups_to_delete = set(non_deform_vgroups) - set(used_vgroups)
            names = [vg.name for vg in groups_to_delete]
            if debug_mode:
                print(f"Deleting unused non-deform groups:")
                print("    " + "\n    ".join(names))
            delete_vgroups(mesh_ob, groups_to_delete)
            return names
        
        print('Performing final cleanup..')
        
        if cage_settings.method != "MESH_DEFORM":
            empty_groups = get_empty_deforming_vgroups(cage)
            num_groups = len(empty_groups)
            delete_vgroups(cage, empty_groups)
            if debug_mode:
                print("Deleted", len(empty_groups), "unselected deform groups.")
        
        deleted_names = delete_unused_vgroups(cage)
        if debug_mode:
            print("Deleted", len(deleted_names), "unused non-deform groups.")
        
        return
    
    def execute(self, context):
        
        cage_settings = context.scene.Simplicage_CreateCageSettings
        
        if not hasattr(bpy.context, "temp_override"):
            self.report({'ERROR'}, "Only Blender versions >= 3.3 are supported.")
            return {'FINISHED'}
        
        # Check that the armature is selected or that the selected mesh has an armature
        if context.active_object != None and context.active_object.type == "ARMATURE":
            armature = context.active_object
        else:
            if context.active_object == None:
                bpy.context.view_layer.objects.active = cage_settings.body
            
            try:
                armature = cage_settings.body.find_armature()
            except:
                armature_mod_avail = len([x for x in cage_settings.body.modifiers if x.type == "ARMATURE"])
                armature = None
                if cage_settings.mode_cage != "VERTEX_GROUP" and armature_mod_avail > 0:
                    self.report({'ERROR'}, "Select a Mesh with an Armature.")
                    return {'FINISHED'}
        
        print('-------------------------------------')
        
        body = cage_settings.body
        body_verts = body.data.vertices
        body_group_names = [g.name for g in body.vertex_groups]
        
        if armature:
            armature.data.pose_position = 'REST'
        
        if "BONE" in cage_settings.mode_cage:
        
            bones = self.main()
            activeBone = context.active_pose_bone

            bone_selected = False
        
            # non_deform_interrupt = False
            # for bone in bpy.context.selected_pose_bones:
            #     if not bpy.data.objects[context.object.name].data.bones[bone.name].use_deform:
            #         print('Error: Bone ', bone.name, ' is not a deforming bone.\n')
            #         non_deform_interrupt = True
        
            # if non_deform_interrupt:
            #     self.report({'ERROR'}, "Select Deforming bones.")
            #     return {'FINISHED'}
            
            if cage_settings.mode_cage == "BONE_CHAIN" and len(bpy.context.selected_pose_bones) == 1:
                cage_settings.mode_cage == "BONE_SINGLE"
                print('Warning: Working as Single Bone mode, as only one bone has been selected.\n')
                                
        if cage_settings.mode_cage == "BONE_CHAIN":
            
            print('Creating a unique Cage for the selected bones:')
            print(bones)
            
            chainName = "Chain-" + bones[-1]
            selected = False;
            selectedOnce = False
            
            for bone in bones:
                
                if bone == bones[0]:
                    self.cleanThings(body , bone , cage_settings , chainName)
                selected = self.selectVerts(body, bone , cage_settings, chainName)   
                if selected == True:
                    selectedOnce = True
                if bone == bones[-1]:
                    if selected == False and selectedOnce == False :
                       break; 
                    
                    cage = self.duplicateMesh(body, armature, bone, cage_settings)              
                    bpy.ops.object.select_all(action='DESELECT')
                    cage.select_set(True)            
                    
                    if cage_settings.clean_selection:
                        self.cleanSelection(cage , cage_settings)
                   
                    if cage_settings.close_mesh:
                        self.closeObject(cage, cage_settings)
                                                   
                    if cage_settings.remesh:
                        is_remeshed = self.remeshObject(cage, cage_settings)
                        if not is_remeshed:
                            self.report({'ERROR'}, "An error occurred while remeshing. Try to re-restart Blender and re-try.")
                            bpy.context.view_layer.objects.active = armature
                            armature.data.pose_position = 'POSE'
                            bpy.ops.object.mode_set(mode = 'POSE')
                            bpy.data.objects.remove(cage, do_unlink=True)
                            return {'FINISHED'}
                        
                    bpy.ops.object.transform_apply(location = True, rotation = True, scale = True)
                
                    if cage_settings.pin_use_proximity_data and cage_settings.close_mesh:
                        self.generateProximityData(cage, body, cage_settings)
                    self.scaleObject(cage, cage_settings)
                    
                    bpy.ops.object.transform_apply(location = True, rotation = True, scale = True)
                                                                       
                    self.transferData(cage, body)
                    
                    bpy.ops.object.select_all(action='DESELECT')
                    self.setWeights(bones, cage, body, cage_settings, activeBone)

                    if cage_settings.fix_influence and cage_settings.mode_phys != 'COLLISION':
                        self.modifyVertexGroupCopy(chainName, cage, body, cage_settings)
               
                    if cage_settings.mode_phys == 'CLOTH':
                        is_bound = self.bindCage(cage, body, armature, bone, cage_settings, chainName)
                        if not is_bound:
                            self.report({'ERROR'}, "An error occurred while binding the mesh. Try with different Coverage and Resolution settings, or change Close Cage Method.")
                            bpy.context.view_layer.objects.active = armature
                            armature.data.pose_position = 'POSE'
                            bpy.ops.object.mode_set(mode = 'POSE')
                            bpy.data.objects.remove(cage, do_unlink=True)
                            return {'FINISHED'}
                        cloth_modifier = self.addClothPhyiscs(cage, body, bone, cage_settings, context)
                        self.orderModifiers(cloth_modifier, cage)
                        if cage_settings.enable_smooth_corr:
                            self.addSmoothCorrModifier(cage, cage_settings)
                        self.loadPreset()
                    elif cage_settings.mode_phys == 'COLLISION':
                        self.addCollisionModifier(cage)
            
        else:
            
            if cage_settings.mode_cage == "VERTEX_GROUP":
                print('Creating a unique Cage for the selected vertex group: ' + cage_settings.vertex_group)
                bones = [cage_settings.vertex_group]
            else:
                print('Creating a Cage for the selected bones:')
                print(bones)  
            
            selected = False
            
            for bone in bones:
                
                print('Creating the cage of \'' + bone + '\'')
                           
                self.cleanThings(body , bone , cage_settings , None)
                selected = self.selectVerts(body, bone , cage_settings , None)
                if selected == False:
                    break;
                cage = self.duplicateMesh(body, armature, bone, cage_settings)
                
                bpy.ops.object.select_all(action='DESELECT')
                cage.select_set(True)
                
                if cage_settings.clean_selection:
                    self.cleanSelection(cage, cage_settings)
                
                if cage_settings.close_mesh:
                    self.closeObject(cage, cage_settings)
                
                if cage_settings.remesh:
                    is_remeshed = self.remeshObject(cage, cage_settings)
                    if not is_remeshed:
                        self.report({'ERROR'}, "An error occurred while remeshing. Try to re-restart Blender and re-try.")
                        bpy.context.view_layer.objects.active = armature
                        armature.data.pose_position = 'POSE'
                        bpy.ops.object.mode_set(mode = 'POSE')
                        bpy.data.objects.remove(cage, do_unlink=True)
                        return {'FINISHED'}
                
                print('Applying transformations to the cage..')
                bpy.ops.object.transform_apply(location = True, rotation = True, scale = True)
                
                if cage_settings.pin_use_proximity_data and cage_settings.close_mesh:
                    self.generateProximityData(cage, body, cage_settings)
                self.scaleObject(cage, cage_settings)
                
                bpy.ops.object.transform_apply(location = True, rotation = True, scale = True)
                
                self.transferData(cage, body)
                self.setWeightsSingle(bone, cage, body, cage_settings)
            
                if cage_settings.fix_influence:
                    self.modifyVertexGroupCopy(bone, cage, body, cage_settings)
               
                if cage_settings.mode_phys == "CLOTH":
                    is_bound = self.bindCage(cage, body, armature, bone, cage_settings, None)
                    if not is_bound:
                        self.report({'ERROR'}, "An error occurred while binding the mesh of \'"+ bone +"\'.  Try with different Coverage and Resolution settings, or change Close Cage Method.")
                        if armature:
                            bpy.context.view_layer.objects.active = armature
                            armature.data.pose_position = 'POSE'
                            bpy.ops.object.mode_set(mode = 'POSE')
                        bpy.data.objects.remove(cage, do_unlink=True)
                        return {'FINISHED'}
                    cloth_modifier = self.addClothPhyiscs(cage, body, bone, cage_settings, context)
                    self.orderModifiers(cloth_modifier, cage)
                    if cage_settings.enable_smooth_corr:
                        self.addSmoothCorrModifier(cage, cage_settings)
                    self.loadPreset()
                elif cage_settings.mode_phys == 'COLLISION':
                    self.addCollisionModifier(cage)
        
        if selected == False:
            bpy.ops.object.select_all(action='DESELECT') 
            bpy.context.view_layer.objects.active = armature
            armature.select_set(True)
            armature.data.pose_position = 'POSE'
            bpy.ops.object.mode_set(mode = 'POSE') 
            return {'FINISHED'}
        
        self.finalCleanup(cage, cage_settings)
        
        bpy.ops.object.select_all(action='DESELECT')    
        
        if armature:
            armature.select_set(True)
            armature.data.pose_position = 'POSE'
        bpy.ops.object.select_all(action='DESELECT')
        
        print('-------------------------------------')
       
        self.report({'INFO'}, "Cage successfully created.")    
    
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Presets
# ------------------------------------------------------------------------

class OpenFileBrowser(bpy.types.Operator):
    """open location"""
    bl_idname = "script.location_presetperso"
    bl_label = "open location of Presets"
   
    def execute(self, context):
        bpy.ops.wm.path_open(filepath=os.path.join(bpy.utils.script_path_user(), 'presets', 'simplicage'))
        return {'FINISHED'}
        

class ExecutePresets(bpy.types.Operator):
    """Execute a preset"""
    bl_idname = "script.execute_presetperso"
    bl_label = "Execute a Python Preset"

    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'SKIP_SAVE'},
    )
    menu_idname: bpy.props.StringProperty(
        name="Menu ID Name",
        description="ID name of the menu this was called from",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        from os.path import basename, splitext
        filepath = self.filepath

        # Change the menu title to the most recently chosen option
        preset_class = getattr(bpy.types, "SIMPLICAGE_MT_display_presets")
        preset_class.bl_label = bpy.path.display_name(basename(filepath))

        ext = splitext(filepath)[1].lower()

        if ext not in {".py", ".xml"}:
            self.report({'ERROR'}, "Unknown file type: %r" % ext)
            return {'CANCELLED'}

        if ext == ".py" and context.mode == "OBJECT":
            try:
                bpy.utils.execfile(filepath)
                bpy.utils.execfile(filepath)
            except Exception as ex:
                self.report({'ERROR'}, "Failed to execute the preset: " + repr(ex))

        elif ext == ".xml":
            import rna_xml
            rna_xml.xml_file_run(context,
                                 filepath,
                                 preset_class.preset_xml_map)     

        return {'FINISHED'}

class SIMPLICAGE_MT_display_presets(Menu):
    bl_label = "Presets"
    preset_subdir = "simplicage"
    preset_operator = "script.execute_presetperso"
    preset_operator_defaults = {
            "menu_idname" : 'SIMPLICAGE_MT_display_presets'
            }
    draw = Menu.draw_preset
    @classmethod
    def poll(cls, context): 
        return True

class simplicage_add_preset(AddPresetBase, bpy.types.Operator):
    '''Save current parameters'''
    bl_idname = "physics.object_display_preset_add"
    bl_label = "Save as a preset"
    preset_menu = "SIMPLICAGE_MT_display_presets"
    @classmethod
    def poll(cls, context):
        if context.active_object != None:
           if context.mode == 'OBJECT' and any([m for m in context.active_object.modifiers if m.type == "CLOTH"]) :                  
               return True
        else:
           return False
    # variable used for all preset values
    preset_defines = [
    
        "obj = bpy.context.active_object",
        "modifier = next(i for i in obj.modifiers if i.type == 'CLOTH')", 
    
    ]

    # properties to store in the preset
    preset_values = [
    
        "modifier.settings.quality",
        "modifier.settings.mass",
        "modifier.settings.air_damping",
        "modifier.settings.time_scale",
        "modifier.settings.tension_stiffness",
        "modifier.settings.compression_stiffness",
        "modifier.settings.shear_stiffness",
        "modifier.settings.bending_stiffness",
        "modifier.settings.tension_damping",
        "modifier.settings.compression_damping",
        "modifier.settings.shear_damping",
        "modifier.settings.bending_damping",
        "modifier.settings.bending_model",
        "modifier.settings.vertex_group_intern",
        "modifier.settings.pin_stiffness",
        "modifier.settings.tension_damping",
        "modifier.settings.compression_damping",
        "modifier.settings.shear_damping",
        "modifier.settings.bending_damping",
        "modifier.settings.use_dynamic_mesh",
        "modifier.settings.use_internal_springs",
        "modifier.settings.internal_tension_stiffness",
        "modifier.settings.internal_compression_stiffness",
        "modifier.settings.internal_tension_stiffness_max",
        "modifier.settings.internal_compression_stiffness_max",
        "modifier.collision_settings.use_collision",
        "modifier.settings.use_pressure",
        "modifier.settings.uniform_pressure_force",
        "modifier.settings.shrink_min",
        "modifier.settings.use_dynamic_mesh",
        "modifier.settings.use_pressure_volume",
        "modifier.settings.target_volume",
        "modifier.settings.pressure_factor",
        "modifier.settings.fluid_density",
        "modifier.collision_settings.collision_quality", 
        "modifier.collision_settings.distance_min",
        "modifier.collision_settings.use_self_collision", 
        "modifier.collision_settings.self_friction",
        "modifier.collision_settings.self_distance_min", 
        "modifier.collision_settings.self_impulse_clamp", 
        "modifier.settings.vertex_group_mass",
        "modifier.settings.tension_stiffness_max", 
        "modifier.settings.compression_stiffness_max", 
        "modifier.settings.shear_stiffness_max", 
        "modifier.settings.bending_stiffness_max", 
        "modifier.settings.use_sewing_springs", 
        "modifier.settings.sewing_force_max", 
        "modifier.settings.effector_weights.gravity",
        "modifier.settings.effector_weights.all",
        "modifier.settings.effector_weights.force",
        "modifier.settings.effector_weights.vortex",
        "modifier.settings.effector_weights.magnetic",
        "modifier.settings.effector_weights.harmonic",
        "modifier.settings.effector_weights.charge",
        "modifier.settings.effector_weights.lennardjones",
        "modifier.settings.effector_weights.wind",
        "modifier.settings.effector_weights.curve_guide",
        "modifier.settings.effector_weights.texture",
        "modifier.settings.effector_weights.smokeflow",
        "modifier.settings.effector_weights.turbulence",
        "modifier.settings.effector_weights.drag",
        "modifier.settings.effector_weights.boid",
        
    ]

    # where to store the preset
    preset_subdir = "simplicage"

# ------------------------------------------------------------------------
#    Cage Manager Modifier
# ------------------------------------------------------------------------

class Simplicage_CageVisibility(bpy.types.Operator):
    """Enable/disable cage visibility (Object modifiers are not disabled)."""
    bl_idname = "physics.cage_visibility"
    bl_label = ""
    bl_options = {'UNDO', 'INTERNAL'}
    
    switch_on: bpy.props.BoolProperty(
        default = True
    )
    
    def execute(self, context):
        
        bodies = list(set([x.Simplicage_CageSettings.body for x in bpy.data.objects if x.Simplicage_CageSettings.bone != ""]))
        for body in bodies:
            for obj in [x for x in bpy.data.objects if x.Simplicage_CageSettings.bone != "" and x.Simplicage_CageSettings.body == body]:
                single_cage_settings = obj.Simplicage_CageSettings
                obj.hide_viewport = not self.switch_on
        
        return {'FINISHED'}

class Simplicage_CageDelete(bpy.types.Operator):
    """Delete the cage."""
    bl_idname = "physics.cage_delete"
    bl_label = ""
    bl_options = {'UNDO', 'INTERNAL'}
    
    cage: bpy.props.StringProperty(
        default = ""
    )
    
    def execute(self, context):
        
        if self.cage == "":
            self.report({'ERROR'}, "Error while deleting the cage. Remove it manually in Viewport or in the Outliner")
            return {'FINISHED'}
        
        obj = bpy.data.objects[self.cage]
        data = obj.data
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(data)
        
        return {'FINISHED'}

class Simplicage_Bake_SyncFrames(bpy.types.Operator):
    """Synchronise the physics bake frames with the scene ones"""
    bl_idname = "simplicage.bake_syncframes"
    bl_label = "Synchornise frames with scene"

    def execute(self, context):
        
        cage_settings = context.scene.Simplicage_CreateCageSettings
        
        cage_settings.frame_start = context.scene.frame_start
        cage_settings.frame_end = context.scene.frame_end
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Panel
# ------------------------------------------------------------------------


class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Simplicage"

class PANEL_PT_Simplicage(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_Simplicage"
    bl_label = "Create Cages"

    def draw(self, context):
        
        debug_mode = bpy.context.preferences.addons[bl_info["name"].lower()].preferences.debug_mode
        
        layout = self.layout
        cage_settings = context.scene.Simplicage_CreateCageSettings
        
        # General settings
        box = layout.box()
        box.label(text="Settings", icon="MODIFIER")
        
        box.prop(cage_settings, 'body')
        
        row = box.row()
        row.prop(cage_settings, 'mode_cage', expand=True)
        row.scale_y = 1.2
        
        if cage_settings.mode_cage == "VERTEX_GROUP" and cage_settings.body != None:
            box.prop_search(cage_settings,'vertex_group', cage_settings.body,"vertex_groups", text="")
        
        row = box.row()
        row.prop(cage_settings, 'mode_phys', expand=True)
        row.scale_y = 1.2
        
        box.prop(cage_settings, 'advanced', toggle=1, icon="TOOL_SETTINGS")
        
        # Cage settings
        box2 = box.box()
        
        box2.enabled = cage_settings.body != None
        
        if cage_settings.advanced:
            box2.label(text="Cage", icon="SPHERE")
        
        if cage_settings.advanced:
            box2.prop(cage_settings, 'threshold')
            box2.prop(cage_settings, 'scale')
        row = box2.row()
        row.prop(cage_settings, 'close_mesh')
        if cage_settings.advanced:
            col = row.column()
            col.enabled = cage_settings.close_mesh
            col.prop(cage_settings, 'filling_method', text="")
        row = box2.row()
        row.prop(cage_settings, 'remesh')
        col = row.column()
        col.enabled = cage_settings.remesh
        col.prop(cage_settings, 'resolution')
        col.prop(cage_settings, 'remesh_seed')
        if debug_mode:
            row = box2.row()
            row.prop(cage_settings, 'voxel_volume')
        
        if cage_settings.advanced:
            row = box2.row()
            row.prop(cage_settings, 'clean_selection')
            col = row.column()
            col.enabled = cage_settings.clean_selection
            col.prop(cage_settings, 'clean_selection_threshold')
        
        box2.prop(cage_settings, 'enable_smooth_corr')
        
        if cage_settings.advanced:
            
            # Pin settings
            box2 = box.box()
            box2.enabled = cage_settings.mode_phys == "CLOTH" and cage_settings.body != None
            box2.label(text="Pin Group", icon="PINNED")

            row=box2.row()
            row.enabled = cage_settings.close_mesh
            row.prop(cage_settings, 'pin_use_proximity_data')
            col=row.column()
            col.enabled = cage_settings.pin_use_proximity_data
            col.prop(cage_settings, 'pin_proximity_data_factor')
            
            box3 = box2.box()
            row=box3.row()
            row.label(text="Normalization:")
            row.prop(cage_settings, 'pin_norm_method', text="")
            if cage_settings.pin_norm_method in ["TANH"]:
                row = box3.row(align=True)
                row.prop(cage_settings, 'tanh_gain')
                row.prop(cage_settings, 'tanh_min')
            if cage_settings.pin_norm_method in ["ARCSCH"]:
                row = box3.row(align=True)
                row.prop(cage_settings, 'arcsch_gain')
                row.prop(cage_settings, 'arcsch_min')
            if cage_settings.pin_norm_method in ["SIGMOID"]:
                row = box3.row(align=True)
                row.prop(cage_settings, 'sigmoid_exp_fact')
                row.prop(cage_settings, 'sigmoid_exp_shift')
                        
        # Parenting settings
        if cage_settings.advanced:
            box2 = box.box()
            box2.enabled = cage_settings.mode_phys == "CLOTH" and cage_settings.body != None
            box2.label(text="Parenting", icon="FILE_PARENT")
            row=box2.row()
            row.enabled = cage_settings.mode_cage == "BONE_SINGLE"
            row.label(text="Deform method:")
            row.prop(cage_settings, 'method', text="")
            row=box2.row()
            row.enabled = cage_settings.method == "MESH_DEFORM"
            row.label(text="Parenting method:")
            row.prop(cage_settings, 'parenting_method', text="")
            row = box2.row()
            row.prop(cage_settings, 'fix_influence')
            col = row.column()
            col.enabled = cage_settings.fix_influence
            col.prop(cage_settings, 'fix_influence_gain')
            box2.prop(cage_settings, 'enable_smooth_corr_body')
                     
        box = layout.box()
        box.label(text = "Cloth Physics Settings", icon = 'PRESET')
        row = box.row()
        box.enabled = cage_settings.mode_phys == "CLOTH"
        row.menu(SIMPLICAGE_MT_display_presets.__name__, text=SIMPLICAGE_MT_display_presets.bl_label)
        row2=row.row(align=True)
        row2.operator(simplicage_add_preset.bl_idname, text="", icon='ADD')
        row2.operator(simplicage_add_preset.bl_idname, text="", icon='REMOVE').remove_active = True
        row2.operator('script.location_presetperso', text="", icon="FILE_FOLDER")
        if cage_settings.mode_phys == "COLLISION":
            layout.operator('physics.createcage', text="Create Collision Box", icon="MOD_PHYSICS")
        else:
            layout.operator('physics.createcage', text= "Create Cage", icon="SPHERE")

class PANEL_PT_Simplicage_ManageCages(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_Simplicage_ManageCages"
    bl_label = "Manage Cages"
    
    @classmethod
    def poll(cls, context):
        return len([x for x in bpy.data.objects if x.Simplicage_CageSettings.bone != ""])>0
    
    def draw(self, context):
        
        layout = self.layout
        cage_settings = context.scene.Simplicage_CreateCageSettings
        
        box = layout.box()
        row = box.row()
        row.label(text="Cages", icon="SPHERE")
        
        bodies = list(set([x.Simplicage_CageSettings.body for x in bpy.data.objects if x.Simplicage_CageSettings.bone != ""]))
        if len(bodies) > 0:
            row2 = row.row(align=True)
            row2.operator('physics.cage_visibility', icon="RESTRICT_VIEW_OFF").switch_on = True
            row2.operator('physics.cage_visibility', icon="RESTRICT_VIEW_ON").switch_on = False
        for body in bodies:
            box2 = box.box()
            box2.label(text=body.name, icon="MESH_DATA")
            box3 = box2.box()
            for obj in [x for x in bpy.data.objects if x.Simplicage_CageSettings.bone != "" and x.Simplicage_CageSettings.body == body]:
                single_cage_settings = obj.Simplicage_CageSettings
                row = box3.row()
                row.label(text=single_cage_settings.bone, icon="MOD_PHYSICS" if single_cage_settings.collision else "BONE_DATA")
                row2 = row.row(align=True)
                row2.prop(obj,'hide_viewport',text="")
                for mod in obj.modifiers:
                    if mod.type=="CLOTH":
                        row2.prop(single_cage_settings,'toggle_physics',text="", icon="PHYSICS")
                    elif mod.type=="COLLISION":
                        row2.prop(obj.collision,'use',text="", icon="PHYSICS")
                    elif mod.type=="CORRECTIVE_SMOOTH":
                        row2.prop(single_cage_settings,'toggle_corrective',text="", icon="MOD_SMOOTH")
                
                row.operator('physics.cage_delete', icon="X").cage = obj.name
        
        box = layout.box()
        box.label(text="Global cache", icon="PHYSICS")
        row = box.row(align=True)
        row.prop(cage_settings, 'frame_start')
        row.prop(cage_settings, 'frame_end')
        row.operator('simplicage.bake_syncframes', text="", icon="UV_SYNC_SELECT")
        row = box.row(align=True)
        row.operator('ptcache.bake_all', text="Bake All").bake=True
        row.operator('ptcache.free_bake_all', text="Delete All Bake")

# ------------------------------------------------------------------------
#    Registering
# ------------------------------------------------------------------------

classes = (Simplicage_CreateCageSettings,
            Simplicage_AddonPrefs,
            Simplicage_CreateCage,
            Simplicage_CageVisibility,
            Simplicage_CageDelete,
            PANEL_PT_Simplicage,
            PANEL_PT_Simplicage_ManageCages,
            ExecutePresets,
            SIMPLICAGE_MT_display_presets,
            simplicage_add_preset,
            Simplicage_Bake_SyncFrames,
            OpenFileBrowser
            )
         
def checkPresets():
    addon_path = os.path.join(bpy.utils.script_path_user(), 'addons', 'simplicage' , 'presets' ) 
    my_presets = os.path.join(bpy.utils.script_path_user(), 'presets', 'simplicage') 

    if not os.path.isdir(my_presets): 
        os.makedirs(my_presets) 
        files = os.listdir(addon_path) 
        # Copy them 
        [os.rename(os.path.join(addon_path,  f), os.path.join(my_presets, f)) for f in files]

def register():
    
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    bpy.types.Scene.Simplicage_CreateCageSettings = bpy.props.PointerProperty(type = Simplicage_CreateCageSettings)
    checkPresets()

def unregister():
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__":
    register()
