# ##### BEGIN GPL LICENSE BLOCK #####

#Copyright (C) 2021 Alberto Gonzalez & Vjaceslav Tissen
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####
# 
import bpy
import os
from bpy.types import Operator
from tempfile import TemporaryDirectory

from bpy.types import Operator

import bgl
import blf

import bmesh

import gpu
from gpu_extras.batch import batch_for_shader

import mathutils
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_line_plane

from bpy_extras.view3d_utils import (
    region_2d_to_vector_3d,
    region_2d_to_origin_3d
)

from bpy_extras.view3d_utils import region_2d_to_location_3d

from bgl import (GL_ALWAYS, GL_BLEND, glDepthFunc, glDisable, glEnable,
                 glPointSize)

from gpu.types import GPUShader
from gpu_extras.batch import batch_for_shader

import time
from struct import pack

from mathutils import geometry
from bpy_extras.io_utils import unpack_list
import fnmatch

from mathutils import Vector
from bpy_extras import view3d_utils

from math import sqrt

from mathutils.kdtree import KDTree

import numpy as np
import random

from bpy.props import IntProperty, FloatProperty, StringProperty

from . import functions

# from . functions import draw_callback_3d
# from . functions import draw_callback_px 

from . functions import setup_swmesh

# DRAW GPU SHADER LINES
def draw_callback_3d(self, context):
    
    #PATH
    path = self.points.copy() #self.points.copy()

    if self.mouse_vert is not None:
        path.append()

    self.shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

    # POINTS, LINES, TRIS, LINE_STRIP, LINE_LOOP,
    # TRI_STRIP, TRI_FAN, LINES_ADJ, TRIS_ADJ, LINE_STRIP_ADJ

    self.batch = batch_for_shader(self.shader, 'LINE_STRIP', {"pos": path})
    alpha_opacity = bpy.context.scene.draw_line_opacity
    line_width = bpy.context.scene.draw_line_width
    color = (1.0, 1.0, 1.0, alpha_opacity)
    if bpy.context.scene.hit_state == True:
        color = (0.1, 0.1, 1.0, alpha_opacity)
    elif bpy.context.scene.hit_state == False:
        color = (1.0, 0.1, 0.1, alpha_opacity)
    bgl.glLineWidth(line_width)
    self.shader.bind()
    self.shader.uniform_float("color", color)
    self.batch.draw(self.shader)
    
    # Fragment shaders for rounded points
    vshader = """
        uniform mat4 ModelViewProjectionMatrix;
        in vec3 pos;
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.999);
        }
    """

    fshader = """

        void main()
        {
            float r = 0.0, delta = 0.0, alpha = 0.0;
            vec2 cxy = 2.0 * gl_PointCoord - 1.0;
            r = dot(cxy, cxy);
            if (r > 1.0) {
                discard;
            }


            gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);


        }
    """



    glPointSize(7)

    bgl.glEnable(bgl.GL_BLEND)

    self.shader_points = GPUShader(vshader, fshader)

    self.batch_points = batch_for_shader(self.shader_points, 'POINTS', {"pos": path})
    self.shader_points.bind()
    self.batch_points.draw(self.shader_points)
    
    

def draw_callback_px(self, context):
    
    if bpy.context.scene.property_status == True:
        x, y = self.mouse_path[-1]
        vertices = (
            (x, y-50), (x+70, y-50),
            (x, y), (x+70, y))

        indices = (
            (0, 1, 2), (2, 1, 3))

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(1)
        shader.bind()
        shader.uniform_float("color", (0, 0, 0, 0.5))
        batch.draw(shader)

        font_id = 0  # XXX, need to find out how best to get this.

        #DRAW 
        font_offset = 10
        blf.position(font_id, x+font_offset, y-font_offset*2, 0)
        blf.size(font_id, 20, 72)
        blf.color(font_id, 1.0, 0.5, 0, 1.0)

        if bpy.context.scene.property_state == '0':
            value = "Size:"
        elif bpy.context.scene.property_state == '1':
            value = "Offset Distance:"
            if self.offset_distance_state == True:

                value = "Offset Distance:"
            else:
                value = "Offset"
        elif bpy.context.scene.property_state == '2':
            value = "Twist:"
#            
        width = context.area.width
        height = context.area.height - context.area.regions[0].height

        xx = width * 0.3
        yy = height * 0.1
        
        hh = 100
        ll = width
        vertices = (
            (0, yy-hh), (ll, yy-hh),
            (0, yy), (ll, yy))

        indices = (
            (0, 1, 2), (2, 1, 3))

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(1) # Set the line width
        shader.bind()
        shader.uniform_float("color", (0, 0, 0, 0.5))
        batch.draw(shader)
        
        frame = str(value) 
                
        blf.draw(font_id, frame)
        
        # restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
            
        font_id = 0  # XXX, need to find out how best to get this.

        # draw some text
        font_offset = 10
        blf.position(font_id, x+font_offset, y-font_offset*4, 0)
        blf.size(font_id, 20, 72)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        
        frame = str(self.delta)[:4] 
                
        blf.draw(font_id, frame)
        
        # restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        
        #HOTKEY PANEL#
        font_id = 0
        blf.color(font_id, 1, 1, 1, 1)
        
        width = context.area.width
        height = context.area.height - context.area.regions[0].height

        x = width * 0.01
        y = height * 0.25
        
        sync = (height * 0.5 * 0.9) / 2
        
        y = sync
        
        blf.position(font_id, x, y-50, 0)
        blf.size(font_id, 50, 50)
        blf.draw(font_id, "CONFIGURE MODE:" )

        blf.color(font_id, 1, 1, 1, 0.7)
        x = width * 0.01
        y = sync /5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "LMB: Apply Value")

        blf.color(font_id, 1, 1, 1, 0.7)
        x = width * 0.25
        y = sync /5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "MOUSEMOVE: Change Wrap Size" )
                
        blf.color(font_id, 1, 1, 1, 0.7)
        x = width * 0.6
        y = sync /5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "O: Offset Distance")
        if self.offset_distance_state == True:
            text = "ON"
            blf.color(font_id, 1.0, 0.5, 0.5, 0.7)
        else:
            text = "OFF"
            blf.color(font_id, 1, 0.5, 1, 0.7)
        
        x = width * 0.72
        y = sync /5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, text)
 
        blf.color(font_id, 1, 1, 1, 0.7)
        x = width * 0.85
        y = sync / 5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "ESC: Exit Modal.")
    else:
        width = context.area.width
        height = context.area.height - context.area.regions[0].height
        x = width *0.3
        y = height*0.1

        h = 100
        l = width    
            
        vertices = (
            (0, y-h), (l, y-h),
            (0, y), (l, y))

        indices = (
            (0, 1, 2), (2, 1, 3))

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(1) # Set the line width
        shader.bind()
        shader.uniform_float("color", (0, 0, 0, 0.66))
        batch.draw(shader)

        font_id = 0
        
        #----------------------------------------------#
        
        blf.color(font_id, 1, 1, 1, 1)
        
        x = width * 0.01
        y = height *0.3
        
        sync = (height * 0.6 * 0.9) / 2
        
        y = sync
        
        blf.position(font_id, x, y-50, 0)
        blf.size(font_id, 50, 50)
        
        if bpy.context.scene.hit_state == True:
            text = " FRONT"
            blf.color(0, 0, 0, 1, 0.5)
        else:
            text = " BACK"
            blf.color(0, 1, 0, 0, 0.5)
        
        blf.draw(font_id, text )
        
        blf.color(0, 1, 1, 1, 1)       
        
        x = width * 0.01
        y = sync/ 5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "LMB: Draw Path" )

        blf.color(font_id, 1, 1, 1, 1)
        x = width * 0.01
        y = sync/ 5
        blf.position(font_id, x, y-30, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "R: Reset Path")

        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        x = width * 0.15
        y = sync/ 5

        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "S: Switch Orientation")

        blf.position(font_id, x, y-30, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "L: Lock Orientation")

        blf.color(font_id, 1, 1, 1, 1)
        x = width * 0.43
        y = sync/ 5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "CTRL+MOUSESCROLL: Resolution")    

        blf.color(font_id, 1, 1, 1, 1)
        x = width * 0.43
        y = sync/ 5
        blf.position(font_id, x, y-30, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "Y: Genearte Curve")
        
        blf.color(font_id, 1, 1, 1, 1)
        x = width * 0.8
        y = sync/ 5
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "ENTER: Generate Wrap")
        
        blf.color(font_id, 1, 1, 1, 1)
        x = width * 0.8
        y = sync/ 5
        blf.position(font_id, x, y-30, 0)
        blf.size(font_id, 35, 35)
        blf.draw(font_id, "ESC: Exit Drawing")
        # BLF drawing routine
        font_id = 0
       
        x = 500
        y = 60
        
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        pass
# draw_handle_3d = bpy.types.SpaceView3D.draw_handler_add(
#             draw_callback_3d, (), "WINDOW", "POST_VIEW")
        
        
# _handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')

class AddCollisionModifier(Operator):
    bl_idname = "object.add_collision_to_target_obj"
    bl_label = "Add Collision Modifier to selected Object"
    bl_description = "Add Collision Modifier to selected Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        #ADD DECIMATE MODIFIER
        bpy.ops.object.modifier_add(type='DECIMATE')
        bpy.context.object.modifiers["Decimate"].name = "SWCollisionDecimate"
        bpy.context.object.modifiers["SWCollisionDecimate"].use_collapse_triangulate = True
        bpy.context.object.modifiers["SWCollisionDecimate"].show_render = False

        bpy.ops.object.modifier_add(type='COLLISION')

        bpy.context.object.modifiers["Collision"].name = "SWCollision"
        bpy.context.active_object.name = "SWCollision_obj"

        bpy.context.object.collision.friction_factor = 0.8
        bpy.context.object.collision.cloth_friction = 70.0
        bpy.context.object.collision.thickness_inner = 0.001
        bpy.context.object.collision.thickness_outer = 0.010

        bpy.context.object.collision.use = False
        bpy.context.active_object.modifiers['SWCollision'].settings.keyframe_insert(data_path="use", frame=0)

        bpy.context.object.collision.use = True
        bpy.context.active_object.modifiers['SWCollision'].settings.keyframe_insert(data_path="use", frame=3)

        return {"FINISHED"}

class RemoveCollisionFromObject(Operator):
    bl_idname = "object.remove_collision_modifier"
    bl_label = "Apply Modifiers from wrapped cloth Object"
    bl_description = "Add Collision Modifier to selected Object"
    bl_options = {'REGISTER', 'UNDO'}

    def removeCollisionModifier(self, context):
        obj = context.active_object

        if obj.modifiers is not None:
            mod = obj.modifiers
            for modifier in mod:
                if modifier.name == "SWCollision":
                    bpy.ops.object.modifier_remove(modifier=modifier.name, report=True)

    def execute(self, context):
        self.removeCollisionModifier(context)
        return {"FINISHED"}


class ShowIntersected(Operator):
    bl_idname = "scene.show_intersected"
    bl_label = "Show Intersection"
    bl_description = "Add Collision Modifier to selected Object"
    bl_options = {'REGISTER', 'UNDO'}

    def showIntersection(self, context):
        if context.space_data.overlay.show_statvis == True:
            context.space_data.overlay.show_statvis = False
        elif context.space_data.overlay.show_statvis == False:
            context.space_data.overlay.show_statvis = True
            context.scene.tool_settings.statvis.type = 'INTERSECT'

    def execute(self, context):
        self.showIntersection(context)
        return {"FINISHED"}

class ApplyWrapClothModifiers(Operator):
    bl_idname = "object.apply_modifiers_cloth_wrap"
    bl_label = "Apply Modifiers from wrapped cloth Object"
    bl_description = "Add Collision Modifier to selected Object"
    bl_options = {'REGISTER', 'UNDO'}

    def applyModifiers(self, context):
        obj = context.active_object

        if obj.modifiers is not None:
            modifiers = obj.modifiers
            for mod in modifiers:
                if "SOLIDIFY" not in mod.type:
                    if "SimplyWrapSmooth" == mod.name:
                        pass
                    else:
                        bpy.ops.object.modifier_apply(modifier=mod.name)

            bpy.ops.object.subdivision_set(level=1, relative=False)

    def changeObjectName(self,context):
        newName = "wrapped"
        bpy.context.active_object.name = newName 

    def execute(self, context):
        self.applyModifiers(context)
        self.changeObjectName(context)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        return {"FINISHED"}

class PlayStopOperator(Operator):
    bl_idname = "object.play_stop"
    bl_label = "Play and Restart Animation"
    bl_description = "Add Collision Modifier to selected Object"
    bl_options = {'REGISTER', 'UNDO'}

    state: StringProperty(default="PLAY")

    def play(self, context):
        
        if "SWCollisionDecimate" in bpy.data.objects["SWCollision_obj"].modifiers:
            bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport = True
        bpy.ops.screen.animation_play(True)

    def stop(self, context):
        bpy.ops.screen.frame_jump(end=False)
        bpy.ops.screen.animation_cancel(True)
        if "SWCollisionDecimate" in bpy.data.objects["SWCollision_obj"].modifiers:
            bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport = True

    def execute(self, context):
        if self.state == "PLAY":
            self.play(context)
        if self.state == "STOP":
            self.stop(context)
        return {"FINISHED"}

class AddCustomObjectToCurve(Operator):
    bl_idname = "object.add_custom_to_curve"
    bl_label = "Add for wrapped curve"
    bl_description = "Add selected object for curve"
    bl_options = {'REGISTER', 'UNDO'}

    state: StringProperty(default="PLAY")

    def addModifiers(self, context):
        bpy.ops.object.modifier_add(type='ARRAY')
        bpy.context.object.modifiers["Array"].fit_type = 'FIT_CURVE'
        bpy.context.object.modifiers["Array"].relative_offset_displace[0] = 0.8
        bpy.context.object.modifiers["Array"].curve = bpy.data.objects["simply_curve"]

        bpy.ops.object.modifier_add(type='CURVE')
        bpy.context.object.modifiers["Curve"].object = bpy.data.objects["simply_curve"]

    def execute(self, context):
        self.addModifiers(context)
        return {"FINISHED"}

class ResetShrinkKeyframesAnimation(Operator):
    bl_idname = "object.reset_shrink_keyframe_animation"
    bl_label = "Reset Shrink Animation"
    bl_description = "Reset shrink keyframe animation"
    bl_options = {'REGISTER', 'UNDO'}

    state: StringProperty(default="PLAY")

    def addKeyframes(self, context):
        simplywrapcloth = context.active_object.modifiers["SimplyWrapCloth"]

        simplywrapcloth.settings.shrink_min = -0.4
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
            data_path='shrink_min', frame=0)

        simplywrapcloth.settings.shrink_min = 0.3
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
            data_path='shrink_min', frame=10)

        simplywrapcloth.settings.shrink_min = 0.4
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
            data_path='shrink_min', frame=15)

        simplywrapcloth.settings.shrink_min = 0.6
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
            data_path='shrink_min', frame=25)

    def execute(self, context):
        self.addKeyframes(context)
        return {"FINISHED"}

class GenerateWrapFromSelectedCurve(Operator):
    bl_idname = "curve.generate_wrap_from_curve"
    bl_label = "Generate Wrap from selected Curve"
    bl_description = "Generate Wrap from selected Curve"
    bl_options = {'REGISTER', 'UNDO'}

    bevelDepth: FloatProperty(default=0.0)

    def convertFromCurveToMesh(self, context):
        self.bevelDepth = bpy.context.active_object.data.bevel_depth
        context.active_object.data.bevel_depth = 0
        bpy.ops.object.convert(target='MESH')
        bpy.context.object.name = "SimplyWrapCurveMesh"
        
    def addModifiers(self, context):
        bpy.ops.object.modifier_add(type='CLOTH')
        context.active_object.modifiers["Cloth"].name = "SimplyWrapCloth"

        simplywrapcloth = context.active_object.modifiers["SimplyWrapCloth"]
        simplywrapcloth.show_viewport = False
        simplywrapcloth.collision_settings.distance_min = 0.01
        simplywrapcloth.collision_settings.use_self_collision = True
        simplywrapcloth.collision_settings.self_distance_min = 0.01
        simplywrapcloth.settings.quality = 20
        simplywrapcloth.collision_settings.collision_quality = 20
        simplywrapcloth.collision_settings.use_self_collision = True
        simplywrapcloth.collision_settings.self_friction = 50.0

        # SHRINK ANIMATION
        simplywrapcloth.settings.shrink_min = -0.4
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
                    data_path='shrink_min', frame=0)

        simplywrapcloth.settings.shrink_min = 0.3
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
                    data_path='shrink_min', frame=10)

        simplywrapcloth.settings.shrink_min = 0.4
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
                    data_path='shrink_min', frame=15)

        simplywrapcloth.settings.shrink_min = 0.6
        bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(
                    data_path='shrink_min', frame=25)

        #SURFACE OFFSET
        simplywrapcloth.collision_settings.distance_min = 0.01
        simplywrapcloth.collision_settings.self_distance_min = 0.01

        simplywrapcloth.settings.time_scale = 0.1
        simplywrapcloth.settings.vertex_group_mass = "PinWrap"

        bpy.ops.object.modifier_add(type='SOLIDIFY')
        bpy.context.active_object.modifiers["Solidify"].name = "SimplyWrapSolidify"
        bpy.context.active_object.modifiers["SimplyWrapSolidify"].offset = 0

        if bpy.context.object.modifiers["SimplyWrapSolidify"].thickness <= 0.01:
            bpy.context.object.modifiers["SimplyWrapSolidify"].thickness = 0.015
        else:
            bpy.context.object.modifiers["SimplyWrapSolidify"].thickness = self.bevelDepth

        bpy.context.object.modifiers["SimplyWrapSolidify"].show_in_editmode = False

        bpy.ops.object.modifier_add(type='SMOOTH')
        bpy.context.active_object.modifiers["Smooth"].name = "SimplyWrapSmooth"

        bpy.ops.object.modifier_add(type='SUBSURF')
        bpy.context.active_object.modifiers["Subdivision"].name = "SimplyWrapSubdivision"

    def execute(self, context):
        self.convertFromCurveToMesh(context)
        self.addModifiers(context)
        bpy.context.object.modifiers["SimplyWrapCloth"].show_viewport = True
        bpy.context.scene.frame_current = 1
        return {"FINISHED"}

class CleanUpWrapEndings(bpy.types.Operator):
    """Remove endings on cloth strip"""
    bl_idname = "mesh.cleanup_endings"
    bl_label = "Clean Up"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode in {'EDIT_MESH'}
    
    def execute(self, context):
        context = bpy.context
        bpy.ops.mesh.select_all(action='DESELECT')

        ob = context.object
        me = ob.data
        bm = bmesh.from_edit_mesh(me)
        for v in bm.verts:
            v.select = len(v.link_edges) == 2

        bmesh.update_edit_mesh(me)
        bpy.ops.mesh.delete(type='VERT')

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.mesh.select_non_manifold(extend=False, use_wire=True, use_boundary=False, use_multi_face=False, use_non_contiguous=False, use_verts=False)
        bpy.ops.mesh.delete(type='EDGE')

        return {'FINISHED'}

class ShowCurveAndMeshInScene(bpy.types.Operator):
    """Remove endings on cloth strip"""
   
    bl_idname = "scene.show_curve_visibility"
    bl_label = "Curve"
    bl_options = {'REGISTER', 'UNDO'}

    mode:StringProperty(default="CURVE")

    def showCurveIfHidden(self, context):
        for obj in bpy.data.objects:
            if "simply_curve" in obj.name:
                if obj.type == "CURVE":
                    if obj.hide_get() == False:
                        obj.hide_set(True)
                    elif obj.hide_get() == True:
                        obj.hide_set(False)
                    break

    def showMeshIfHidden(self, context):
        for obj in bpy.data.objects:
            if "SimplyWrapMesh" in obj.name:
                if obj.type == "MESH":
                    if obj.hide_get() == False:
                        obj.hide_set(True)
                    elif obj.hide_get() == True:
                        obj.hide_set(False)
                    break

    def execute(self, context):
        if self.mode == "CURVE":
            self.showCurveIfHidden(context)
        elif self.mode == "MESH":
            self.showMeshIfHidden(context)
        return {'FINISHED'}

class AssignSelectionToPinGroup(bpy.types.Operator):
    """Remove endings on cloth strip"""
   
    bl_idname = "object.assign_pin_from_selected"
    bl_label = "Assign"
    bl_options = {'REGISTER', 'UNDO'}

    mode:StringProperty(default="CURVE")

    def createGroupAndAssign(self, context):
        mesh = bpy.data.objects["SimplyWrapMesh"]
        pingroup = mesh.vertex_groups.new(name='PinWrap')
        bpy.ops.object.vertex_group_assign()
        mesh.modifiers["SimplyWrapCloth"].settings.vertex_group_mass = pingroup.name

    def addWeightToPinGroup(self, context):
        bpy.ops.object.vertex_group_assign()

    def execute(self, context): 
        if "SimplyWrapMesh" in bpy.data.objects:
            obj = bpy.data.objects["SimplyWrapMesh"]
        elif "wrapped" in bpy.data.objects:
            obj = bpy.data.objects["SimplyWrapMesh"]
        if "PinWrap" not in bpy.data.objects["SimplyWrapMesh"].vertex_groups:
            self.createGroupAndAssign(context)
        elif "PinWrap" in bpy.data.objects["SimplyWrapMesh"].vertex_groups:
            self.addWeightToPinGroup(context) 
        
        # bpy.ops.object.editmode_toggle()
        return {'FINISHED'}

class RH_OT_reset_handlers(bpy.types.Operator):
    """Reset Handlers"""
   
    bl_idname = "object.reset_handlers"
    bl_label = "Reset"
    bl_options = {'REGISTER', 'UNDO'}

    
    def execute(self, context):
        
        
#        self.unregister_handlers(args, context)
#        
        
        #self.unregister_handlers(context)
        bpy.context.scene.modal_wrap_status = False
        
#        args = (self, context)
        #bpy.types.SpaceView3D.draw_handler_remove(draw_callback_3d, "WINDOW")
        #bpy.types.SpaceView3D.draw_handler_remove(draw_callback_px, "WINDOW")
        
        
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
                
                
        return {'FINISHED'}
    
    
class OT_draw_operator(Operator):
    bl_idname = "object.modal_wrap"
    bl_label = "Draw Modal Operator"
    bl_description = "Operator for drawing"
    bl_options = {'REGISTER', 'UNDO'}

    def __init__(self):
        self.draw_handle_3d = None
        self.draw_event = None
        self.vertices = []
        self.points = []
        self.mouse_vert = None
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)

    def invoke(self, context, event):
        
        if "SWCollision_obj" in bpy.data.objects:
            if bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport== True:
                bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport = True
            if bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport== False:
                bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport = True

        for obj in bpy.data.objects:
            if obj.type == "CURVE":
                if "simply_curve" in obj.name:
                    obj.name = "curve_"
        bpy.context.scene.modal_wrap_status = True
        self.og_obj = bpy.context.active_object
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        if bpy.context.object.modifiers["SWCollisionDecimate"].ratio == 1.0:
            bpy.context.object.modifiers["SWCollisionDecimate"].ratio = 0.1

        self.obj = bpy.context.active_object
        self.obj.update_from_editmode()
        
        deg = bpy.context.view_layer.depsgraph
        me = self.obj.evaluated_get(deg).to_mesh()
        
        self.bm = bmesh.new()
        self.bm.from_mesh(me)
    
        self.region = context.region
        self.rv3d = context.region_data  
        
        if context.space_data.type == 'VIEW_3D':
            args = (self, context)
            self.register_handlers(args, context)
        
        self.bvhtree = self.bvhtree_from_object(context, context.active_object)
        self.active = False
        self.start_loc = None
        self.front_hit = Vector()
        self.back_hit = Vector()
        self.end_loc = Vector()
        self.co = Vector()
        self.index = IntProperty()
        self.dist = 0
        self.num = 0.0
        self.scroll_value = 20
        self.offset = Vector()
        self.set_wheel_zoom_state = False
        self.startPosX = 0
        self.radius = 0
        self.mouse_path = []
        
        bpy.context.scene.property_state = '0'
        context.window_manager.modal_handler_add(self)
        self.offset_value = bpy.context.scene.offset_value

        self.toggle = True
        self.mouse_pos = [0,0]
        self.loc = [0,0,0]
        self.object = None
        self.view_point = None
        self.view_vector = None
        self.world_loc = None
        self.loc_on_plane = None
		
        self.offset_distance_state = False       
        return {"RUNNING_MODAL"}

    def register_handlers(self, args, context):
        self.draw_handle_3d = bpy.types.SpaceView3D.draw_handler_add(
                                draw_callback_3d, args, "WINDOW", "POST_VIEW")
        
        
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
                                draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        
#        
#        self.draw_help_panel = bpy.types.SpaceView3D.draw_handler_add(
#            draw_callback_px2, args, "WINDOW", "POST_VIEW")
#        
#        
    def unregister_handlers(self, context):

        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_3d, "WINDOW")
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, "WINDOW")

        self.draw_handle_3d = None
        self.draw_event = None
        self.bvhtree = None

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

    def get_origin_and_direction(self, event, context):
        mxy = event.mouse_region_x, event.mouse_region_y
    
        region = context.region
        rv3d = context.region_data
        if rv3d:
            origin = region_2d_to_origin_3d(region, rv3d, mxy)
            direction = region_2d_to_vector_3d(region, rv3d, mxy)
        return origin, direction

    def get_mouse_3d_on_plane(self, event, context):
        origin, direction = self.get_origin_and_direction(event, context)
        return intersect_line_plane(origin, origin + direction, 
        self.hit, self.normal)
        
    def point_array(self,context, points, n_count=0, eps=0.001):
        
        bpy.ops.ed.undo_push()
        tot_length = 5

        for i in range(len(points)-1):
            pt1 = points[i]
            pt2 = points[i+1]
            tot_length += (pt1 - pt2).length 
            
        cost = tot_length/ (n_count-1) 
        
        new_array = [points[0]] 
            
        wallet = 0
        
        tip = 0
        for i in range(len(points)-1):
            pt1 = points[i]
            pt2 = points[i+1]
 
            tip = (pt1 - pt2).length 
            wallet += tip 

            while  (wallet - cost) > -eps:
                wallet -= cost 
                fac = -(wallet - tip) / tip  

                new_array.append(pt1.lerp(pt2, fac))

        return new_array

    def get_closest_point(self, context, points, target):
        
        size = len(points)
        kd = mathutils.kdtree.KDTree(size)

        #filter = [i for i in points]
        
        for i, v in enumerate(points):
            
            kd.insert(Vector(v), i)
            
        kd.balance()

        # Find the closest point to the center
#        co_find = (0.0, 0.0, 0.0)
#        co, index, dist = kd.find(co_find)
       
        # 3d cursor relative to the object data
        co_find = target

        # Find the closest 10 points to the 3d cursor
        # print("Close 10 points")
        for (co, index, dist) in kd.find_n(co_find, 10):
            
            
            
            return co, index, dist



    def get_closest_point_limit(self, context, points, target):
        
        size = len(points)
        kd = mathutils.kdtree.KDTree(size)

        #filter = [i for i in points]
        
        for i, v in enumerate(points):
            first_half = (int(len(points)) / 2) /2
                        
            if i >= len(points)-first_half and i is not 0:
                kd.insert(Vector(v), i)
            
        kd.balance()


        # Find the closest point to the center
#        co_find = (0.0, 0.0, 0.0)
#        co, index, dist = kd.find(co_find)
       
        # 3d cursor relative to the object data
        co_find = target

        # Find the closest 10 points to the 3d cursor
        # print("Close 10 points")
        for (co, index, dist) in kd.find_n(co_find, 10):
            return co, index, dist
        
    def execute(self, context):
        if context.area.type != 'VIEW_3D':
            # print("Must use in a 3d region")
            return {'CANCELLED'}

            self.set_wheel_zoom_state = False

        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        self.set_wheel_zoom_state = True
    



    
    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()
        try:
            for region in context.area.regions:
                if(region.x <= event.mouse_x < region.x + region.width  and
                region.y <= event.mouse_y < region.y + region.height and
                region.type in ("HEADER","TOOLS", "UI", "TOOL_PROPS")):   
                
                    return {'PASS_THROUGH'}

            # MODAL SHORTCUT ESC = ESCAPE
            if event.type in {"ESC"}:
                bpy.context.scene.modal_wrap_status = False
                self.unregister_handlers(context)
                self.cancel(context)

                bpy.context.scene.property_status = False
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

                if bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport== True:
                    bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport = False
                self.startPosX = 0
                return {'CANCELLED'}

            # MODAL SHORTCUT LEFT CRTL = LEFT CONTROL BUTTON
            if event.type == 'LEFT_CTRL':
                if event.value == 'PRESS':
                    pass
            self.mouse_path.append((event.mouse_region_x, event.mouse_region_y))
            
            #SCROLL EVENT
            if event.ctrl:
                speed = 3
                
                if event.type in {'WHEELUPMOUSE'}:
                    self.scroll_value = min(200 ,self.scroll_value + speed)

                    if self.vertices:
                        self.points = self.point_array(context,self.vertices, self.scroll_value )
                    return {'RUNNING_MODAL'}

                if event.type in {'WHEELDOWNMOUSE'}:
                    self.scroll_value = max(33,self.scroll_value - speed) 
                    
                    if self.vertices:
                        self.points = self.point_array(context,self.vertices, self.scroll_value)

                    return {'RUNNING_MODAL'}
                

            if event.type == 'MOUSEMOVE':
                if bpy.context.scene.property_status == True:
                    if 'SimplyWrapMesh' in bpy.data.objects:
                        
                        if bpy.context.scene.property_state == '1':
                            self.delta = max(min((event.mouse_x - self.startPosX) *0.01, 5), -1.0) 
                            if bpy.context.scene.shrink_curve == True:
                                bpy.data.objects['simply_curve'].modifiers["CurveWrap"].offset = self.delta
                            else:
                                bpy.context.scene.property_state = '2'
                        
                        elif bpy.context.scene.property_state == '2':
                            
                            self.delta = max(min(event.mouse_x - self.startPosX , 50), 0)
                        
                            bpy.data.objects['simply_curve'].data.twist_smooth = self.delta
                            
                        elif bpy.context.scene.property_state == '0':
                            
                            self.delta = max(min((event.mouse_x - self.startPosX) *0.01, 4), 2) 
                            
                            bpy.data.objects['SimplyWrapMesh'].modifiers["StripSize"].factor = self.delta
                        pass
                else:
                    pass

                #self.report({'INFO'}, str(self.radius))

            #self.delta = max(min((event.mouse_x - self.startPosX) / 2, 1), 0) 
                
            #if event.type == "MOUSEMOVE":
            #if self.active:
            
            #IF HIT DETECTED SET FRONT/BACK HIT ACCORDINIGLY, ALSO SET SELF.OFFSET TO GET STARTING LOCATION
            #if self.hit:
            #loc= self.get_mouse_3d_on_plane(event, context)

            
            
            self.mouse_pos = event.mouse_region_x, event.mouse_region_y
            self.bvhtree = self.bvhtree_from_object(context, self.og_obj)


            #Contextual active object, 2D and 3D regions
            # 
            # self.object = bpy.context.object
            region = bpy.context.region
            region3D = bpy.context.space_data.region_3d

            #The direction indicated by the mouse position from the current view
            self.view_vector = view3d_utils.region_2d_to_vector_3d(region, region3D, self.mouse_pos)
            #The view point of the user
            self.view_point = view3d_utils.region_2d_to_origin_3d(region, region3D, self.mouse_pos)
            #The 3D location in this direction
            self.world_loc = view3d_utils.region_2d_to_location_3d(region, region3D, self.mouse_pos, self.view_vector)

            plane = self.og_obj
            
            self.loc_on_plane = None
            #if plane:
            
            world_mat_inv = plane.matrix_world.inverted()
            # Calculates the ray direction in the target space
            rc_origin = world_mat_inv @ self.view_point
            rc_destination = world_mat_inv @ self.world_loc
            rc_direction = (rc_destination - rc_origin).normalized()
            hit, loc, norm, index = plane.ray_cast( origin = rc_origin, direction = rc_direction )
            
            hit1, location1, normal, index, object, mat =\
            context.scene.ray_cast( context.view_layer.depsgraph , origin = rc_origin, direction= rc_direction)
            
            if hit:
                hit2, location2, normal, index, object, mat =\
                context.scene.ray_cast( context.view_layer.depsgraph, location1 - 0.001 * normal , -normal )


            
                self.radius = (location1 - location2).length
                
            #GET ORIGIN, DIRECTION
            origin, direction = self.get_origin_and_direction(event, context)
            #RAYCAST HIT
            
            try:
                self.hit, self.normal, *_ = self.bvhtree.ray_cast(rc_origin, rc_direction)
            except:
                pass
          


            self.loc_on_plane = loc
            if hit:
                self.world_loc = plane.matrix_world @ loc
               
                #BACKFACES
                self.back_hit, self.normal, *_ = self.bvhtree.ray_cast(self.world_loc + 0.001 * rc_direction  , rc_direction )
                #FRONTFACES
                self.front_hit, self.normal = self.world_loc , norm #self.bvhtree.ray_cast(self.world_loc,direction)#location1, normal#self.bvhtree.ray_cast(origin, direction)
                
                if bpy.context.scene.hit_state == True:
                
                    self.offset = self.front_hit
                    
                else:
                
                    self.offset = self.back_hit
             
            #OTHERWISE CONTINUE FROM LAST POINT
            #else:
          
            if self.vertices:
                    
                count = len(self.vertices) -1
                
                self.offset =  self.vertices[count]
                
                   
            else:
                
                
                pass

            #else:
                
            #            
            #            if self.delta == 0:
            #                
            #                bpy.context.scene.hit_state = True
            #            else:
            #                bpy.context.scene.hit_state = False
            #            
        
            #MOVE POINTS TEST
            #
            x,y = event.mouse_region_x, event.mouse_region_y
                    
            region = context.region
            rv3d = context.space_data.region_3d
            
            if event.type == "MOUSEMOVE":
                obj = bpy.context.active_object
                deg = bpy.context.view_layer.depsgraph
                me = obj.evaluated_get(deg).to_mesh()
                me_data = obj.data
                bm = bmesh.new()
                bm.from_mesh(me)
            
                verts = [ obj.matrix_world @ v.co for v in bm.verts ]

                if self.active:
                    #self.co, self.index, self.dist = self.get_closest_point(context, points=verts, target= self.vertices[i])
                            
                    #if self.hit is None:
                    
                    #self.vertices = self.point_array(context,self.points, bpy.context.scene.point_count )
                    
                    #calculate distance from all points, to the nearest object vertex.
                    #if distance breaks, ignore smoothing. this is so that points dont go through surface.
                    for i, v in enumerate(self.vertices):
                        # x--o--o--o--o-,
                        #               o  
                        #              ,'   Example: [ i > len(self.vertices)-3 ]
                        #             o
                        #             '--o
                        x = 0
                        #trying to smooth last 10 points, ignore first point
                        first_half = (int(len(self.vertices)) / 2) /2
                            
                            
                        if self.hit:
                            pass
                        else:
                            matrix = self.og_obj.matrix_world
                            
                            if i >= len(self.vertices)-first_half and i is not x:
                                co, index, dist = self.get_closest_point(context, points=verts, target= self.vertices[i])

                                pt1 = self.vertices[i]
                                pt2 = self.vertices[i-1]#self.vertices[i-1]#len(self.vertices)-1

                                factor = bpy.context.scene.path_smoothing
                                if bpy.context.scene.hit_state == True:
                                
                                    value = matrix @ pt1.lerp(pt2, factor) + -normal * 0.8 #* 4#0.005 
                                    self.vertices[i] = value
                                else:
                                    value = matrix @  pt1.lerp(pt2, factor) -  -normal * 0.8#* 4#0.005
                                    self.vertices[i] = value
                        
                        factor = bpy.context.scene.path_smoothing
                        if i >= len(self.vertices)-first_half and i is not x:
                            co, index, dist = self.get_closest_point(context, points=verts, target= self.vertices[i])
                        
                            while dist >= 0.8:
                                if dist < 2.0:
                                    pass
                                else:
                                    pt1 = self.vertices[i]
                                    pt2 = self.vertices[i-1]       
                                    self.vertices[i] = pt1.lerp(pt2 , 0.01)     
                                break
            x,y = event.mouse_region_x, event.mouse_region_y
                    
            region = context.region
            rv3d = context.space_data.region_3d
            if self.active and  event.type == "MOUSEMOVE":
                
                #TOGGLE FRONT OR BACK DETECTION BASED ON BOOLEAN STATE
                #self.report({'INFO'}, str(self.index))
                value = self.radius 
                bpy.ops.ed.undo_push()
                # try:
                    
                #if self.hit:
                #STEPPING LENGTH
                obj = self.og_obj
                length_factor = sum(d / s for d, s in zip(obj.dimensions, obj.scale))
                #self.length = 0.1
                    #First 15
                filter = [x for x in self.vertices[0:15]]
                try:
                    if self.vertices:
                        #POINT LOCATION CONTROL#
                
                        
                        # bpy.ops.ed.undo_push()
                        # offset_value = bpy.context.scene.offset_value
                        overlap_dist = bpy.context.scene.overlap_dist
                        overlap_value = bpy.context.scene.overlap_value

                        #offset_value = bpy.context.scene.offset_value

                        #FRONT
                        if bpy.context.scene.hit_state == True:
                            vec = region_2d_to_location_3d(region, rv3d, (x, y), (self.front_hit))
                            vec2 = region_2d_to_location_3d(region, rv3d, (x, y), (vec)) #+ self.offset * 0.07
        
                            matrix = self.og_obj.matrix_world#.inverted()
                            if hit:
                                self.offset = vec2
                            else:
                                self.offset = vec2 
                        #BACK
                        else:

                            vec = region_2d_to_location_3d(region, rv3d, (x, y), (self.back_hit))
                            vec2 = region_2d_to_location_3d(region, rv3d, (x, y), (vec)) #- self.offset * 0.07
            
                            matrix = self.og_obj.matrix_world#.inverted()
                    
                            if hit:
                                self.offset = vec2 
                            else:
                                self.offset = vec2
                except:
                    bpy.context.scene.modal_status = False
                    self.unregister_handlers(context)
                #APPENDING 
                if 'SimplyWrapMesh' in bpy.data.objects:
                    pass
                else:
                    bpy.ops.ed.undo_push()
                    
                    vec = region_2d_to_location_3d(region, rv3d, (x, y), (self.offset)) 
                    vec2 = region_2d_to_location_3d(region, rv3d, (x, y), (vec))

                    matrix = self.og_obj.matrix_world
                    
                    co = 0
                    index = 0
                    dist = 0

                    overlap_dist = bpy.context.scene.overlap_dist
                    overlap_value = bpy.context.scene.overlap_value 
                    #get self.points and ignore the first 15
                    
                    
                    points = [x for x in self.points[0:len(self.points)-10] ]

                    try:
                        if self.vertices:
                            self.co, self.index, self.dist = self.get_closest_point(context, points= points, target= vec2)
                    except:
                        pass
                
                    vec_co = region_2d_to_location_3d(region, rv3d, (x, y), (self.co))


                    if len(self.vertices) > 10:
                            
                        while self.dist <= overlap_dist:
                            self.offset_value = bpy.context.scene.offset_value + overlap_value 
                            
                            break
                        else:
                            self.offset_value = bpy.context.scene.offset_value
                    else:
                        self.offset_value = bpy.context.scene.offset_value
                        
                    #offset_value = bpy.context.scene.offset_value

                    
                    #self.report({'INFO'}, str(self.index))
                    
                    if bpy.context.scene.hit_state == True:
                        #0.05# region_2d_to_location_3d(region, rv3d, (x, y), (self.front_hit )) *0.1
                        #loc = matrix @ vec2
                        
                        self.vertices.append(matrix @ vec2 + -rc_direction * (self.offset_value * self.radius ) )
                            
                    else:
                        #0.5 #- region_2d_to_location_3d(region, rv3d, (x, y), (self.back_hit )) *0.1
                        #loc = matrix @ vec2 
                    
                        self.vertices.append(matrix @ vec2 - -rc_direction * (self.offset_value * self.radius ) ) 
                            
                    if self.vertices:
                        
                
                        self.points = self.point_array(context,self.vertices, bpy.context.scene.point_count )
                #SMOOTH OUT SELF.POINTS A BITself.radius

                return {"RUNNING_MODAL"}

            if event.type == 'LEFTMOUSE':
                bpy.ops.ed.undo_push()
                ob = bpy.context.object

                if bpy.context.scene.property_status == True:
                    pass
                else:
                    if hit:
                        #BACKFACES
                        back_hit, normal, *_ = self.bvhtree.ray_cast(self.world_loc + 0.001 * rc_direction, rc_direction)
                        #FRONTFACES
                        front_hit, normal = self.world_loc , norm #self.bvhtree.ray_cast(origin, direction)

                        if bpy.context.scene.hit_state == True:
                            self.start_loc = self.world_loc #FRONTFACES
                        else:
                            self.start_loc = back_hit #BACKFACES
                    if self.active:
                        if self.start_loc:
                            pass
                            
                self.active = event.value == 'PRESS'
                
                if event.value == 'PRESS':
                    pass
                elif event.value == 'RELEASE':
                    if self.vertices:
                        pass
                    else:
                        pass

                    if bpy.context.scene.lock_draw_orientation == True:
                        pass
                    elif bpy.context.scene.lock_draw_orientation == False:
                        bpy.context.scene.hit_state = not bpy.context.scene.hit_state

                    if 'SimplyWrapMesh' in bpy.data.objects:
                        #event.mouse_x
                        value = int(bpy.context.scene.property_state) + 1
                        # if value <2:
                        bpy.context.scene.property_state = str(value)

                        if bpy.context.scene.property_state == '3':
                            bpy.context.scene.property_status = False
                            bpy.context.scene.frame_current = 1

                            # Turn on Viewport for Subdivision Modifier on Wrapped Mesh
                            
                            try:
                                wrap = bpy.data.objects['SimplyWrapMesh']
                                wrap.modifiers['SimplyWrapSubdivision'].show_viewport = True
                                wrap.modifiers['SimplyWrapSubdivision'].show_in_editmode = True
                            except:
                                pass
                            #UNTANGLE SIM
                            bpy.ops.screen.animation_play()
                            bpy.context.active_object.show_in_front = False

                            def untangle(scene):
                                pause= 5
                                frameone= 1
                                # print("Frame Change", bpy.context.scene.frame_current)
                                if bpy.context.scene.frame_current == 5:
                                    bpy.ops.screen.animation_cancel()
                                    bpy.context.scene.frame_current = pause
                                    bpy.context.scene.frame_current = frameone

                                    #ENABLE CLOTH AGAIN AFTER UNTANGLING 
                                    mesh = bpy.data.objects['SimplyWrapMesh']
                                    
                                    mesh.modifiers["SimplyWrapCloth"].show_viewport = True
                                    

                                    mesh.modifiers["SimplyWrapCloth"].collision_settings.distance_min = 0.01
                                    #mesh.modifiers["SimplyWrapCloth"].settings.shrink_min = self.radius / 2
                                    
                                    bpy.ops.screen.animation_play()
                                    #remove simplycurve at the end. no need for now
                                    # objs = bpy.data.objects
                                    # objs.remove(objs["simply_curve"], do_unlink=True)
                                    if "simply_curve" in bpy.data.curves: 
                                        bpy.context.view_layer.objects['simply_curve'].hide_set(True)

                                    for i in range( len( bpy.app.handlers.frame_change_pre ) ):
                                        bpy.app.handlers.frame_change_pre.pop()
                                
                            bpy.app.handlers.frame_change_pre.append(untangle)
                            #after you untangle do this:
                            
                            mesh = bpy.data.objects['SimplyWrapMesh']
                            
                            bpy.ops.object.select_all(action='DESELECT')

                            context.view_layer.objects.active = mesh
                            mesh.select_set(True)
                            
                            bpy.ops.object.modifier_apply(modifier="StripSize", report=True)
                            bpy.ops.object.modifier_apply(modifier="SimplyArray", report=True)
                            bpy.ops.object.modifier_apply(modifier="SimplyCurve", report=True)

                            #PIN ENDINGS
                            bpy.ops.object.editmode_toggle()
                            bpy.ops.mesh.select_all(action='DESELECT')

                            context = bpy.context

                            ob = context.object
                            me = ob.data
                            bm = bmesh.from_edit_mesh(me)
                            for v in bm.verts:
                                v.select = len(v.link_edges) == 2

                            bmesh.update_edit_mesh(me)
                            
                            #setup vgroups
                            pin_group1 = mesh.vertex_groups.new(name='PinWrap')
                            bpy.ops.object.vertex_group_assign()

                            bpy.ops.object.editmode_toggle()
                            
                            simplywrapcloth = mesh.modifiers["SimplyWrapCloth"]
                            
                            simplywrapcloth.settings.vertex_group_mass = "PinWrap"
                            bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport = False
                            self.unregister_handlers(context)
                            return {'FINISHED'}
                    else:
                        pass            
                #return {"RUNNING_MODAL"}

            # MODAL SHORTCUT RETURN = CREATE CURVE
            if event.type == 'RET':
                if event.value == 'PRESS':
                    pass
                elif event.value == 'RELEASE':
                    if bpy.context.scene.property_status == False:
                        bpy.context.scene.modal_wrap_status = False
                        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
                        bpy.context.scene.modal_wrap_status = False
                        self.create_curve(context)
                        
                        self.vertices = []
                        self.points = []

                        bpy.context.scene.property_status = True
                        self.startPosX = event.mouse_x
                        
                    return {"RUNNING_MODAL"}
            # MODAL SHORTCUT RETURN = CREATE CURVE
            if event.type == 'Y':
                if event.value == 'PRESS':
                    pass
                elif event.value == 'RELEASE':
                    bpy.context.scene.modal_wrap_status = False
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

                    self.create_curve_during_modal(context)
                    
                    self.vertices = []
                    self.points = []

                    bpy.context.scene.property_status == False
                    self.unregister_handlers(context)
                    self.cancel(context)
                    # bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
                    bpy.data.objects["SWCollision_obj"].modifiers["SWCollisionDecimate"].show_viewport = True

                    self.startPosX = 0
                    return {"CANCELLED"}

            # MODAL SHORTCUT S = SIZE
            if event.type == 'S':
                if event.value == 'PRESS':
                    pass
                elif event.value == 'RELEASE':
                    if bpy.context.scene.property_status == True:
                        bpy.context.scene.property_state = '0'
                    elif bpy.context.scene.property_status == False:
                        if bpy.context.scene.hit_state == True:
                            bpy.context.scene.hit_state = False
                        elif bpy.context.scene.hit_state == False:
                            bpy.context.scene.hit_state = True
                    
                return {"RUNNING_MODAL"}

            # MODAL SHORTCUT L = LOCK ORIENTATION
            if event.type == 'L':
                if event.value == 'PRESS':
                    pass
                elif event.value == 'RELEASE':
                    if bpy.context.scene.lock_draw_orientation == True:
                        bpy.context.scene.lock_draw_orientation = False
                    elif bpy.context.scene.lock_draw_orientation == False:
                        bpy.context.scene.lock_draw_orientation = True
                return {"RUNNING_MODAL"}

            # MODAL SHORTCUT T = TWIST
            if event.type == 'T': 
                if bpy.context.scene.property_status == True:
                    if event.value == 'PRESS':
                        pass
                    elif event.value == 'RELEASE':
                        bpy.context.scene.property_state = '2'
                        bpy.context.scene.property_status = True
                
                return {"RUNNING_MODAL"}

            # MODAL SHORTCUT O = OFFSET
            if event.type == 'O':
                if bpy.context.scene.property_status == True:
                    if event.value == 'PRESS':
                        pass
                    elif event.value == 'RELEASE':
                        
                        bpy.context.scene.property_state = '1'
                        bpy.context.scene.property_status = True
                        self.offset_distance_state ^= True
                        if "CurveWrap" in  bpy.data.objects['simply_curve'].modifiers:
                            curve = bpy.data.objects['simply_curve'].modifiers['CurveWrap']

                            if self.offset_distance_state == True:
                                curve.show_viewport = True
                            else:
                                curve.show_viewport = False
                return {"RUNNING_MODAL"}

            # MODAL SHORTCUT R = RESET
            if event.type == 'R':
                if event.value == 'PRESS':
                    pass
                elif event.value == 'RELEASE':
                    self.vertices = []
                    self.points = []

                return {"RUNNING_MODAL"}        
        except:
            pass
        
        return {"PASS_THROUGH"}

    def finish(self):
        self.unregister_handlers(context)
        return {"FINISHED"}

    # CREATE CURVE
    def create_curve(self, context):

        bpy.ops.ed.undo_push()
        #CONNECT POINTS AND CREATE EDGES
        ob = bpy.context.object

        pts = self.points  .copy()
        if self.mouse_vert is not None:
            pts.append(self.mouse_vert)
        
        verts = pts

        vertData = []

        for vert in verts:
            # print(vert)
            vertData.append(vert)

        scn = bpy.context.scene
        myMesh = bpy.data.meshes.new('myMesh')
        
        edgeData = []
        a=[]
        b=[]

        for number in range(len(vertData)-1):
            a.append(number)
            b.append(number+1)

        edgeData = list(zip(a, b))

        faceData = ()

        bpy.ops.object.editmode_toggle()

        myMesh.from_pydata(vertData, edgeData, faceData)
        myMesh.update()

        bpy.ops.object.editmode_toggle()

        meshOb = bpy.data.objects.new('simply_curve', myMesh)
        bpy.context.collection.objects.link(meshOb)
        meshOb.show_in_front = True

        bpy.ops.object.select_all(action='DESELECT')

        bpy.context.view_layer.objects.active = meshOb
        meshOb.select_set(True)
        bpy.ops.object.convert(target='CURVE')
        meshOb.data.twist_mode = 'Z_UP'
        
        #hook endpoints
        bpy.ops.object.editmode_toggle()
        bpy.ops.curve.select_all(action='DESELECT')
        bpy.ops.curve.de_select_first()

        setup_swmesh(self,context)

    def create_curve_during_modal(self, context):
        
            bpy.ops.ed.undo_push()
            #CONNECT POINTS AND CREATE EDGES
            ob = bpy.context.object

            pts = self.points  .copy()
            if self.mouse_vert is not None:
                pts.append(self.mouse_vert)
            
            verts = pts

            vertData = []

            for vert in verts:
                # print(vert)
                vertData.append(vert)

            scn = bpy.context.scene
            myMesh = bpy.data.meshes.new('myMesh')
            
            edgeData = []
            a=[]
            b=[]

            for number in range(len(vertData)-1):
                a.append(number)
                b.append(number+1)

            edgeData = list(zip(a, b))

            faceData = ()

            bpy.ops.object.editmode_toggle()

            myMesh.from_pydata(vertData, edgeData, faceData)
            myMesh.update()

            bpy.ops.object.editmode_toggle()

            meshOb = bpy.data.objects.new('simply_curve', myMesh)

            bpy.context.collection.objects.link(meshOb)

            meshOb.show_in_front = True
            
            bpy.ops.object.select_all(action='DESELECT')

            bpy.context.view_layer.objects.active = meshOb
            
            meshOb.select_set(True)
            
            bpy.ops.object.convert(target='CURVE')
            
            meshOb.data.twist_mode = 'Z_UP'
            
            #hook endpoints
            bpy.ops.object.editmode_toggle()
            bpy.ops.curve.select_all(action='DESELECT')
            bpy.ops.curve.de_select_first()
            bpy.ops.object.editmode_toggle()

            bpy.ops.object.modifier_add(type='SUBSURF')
            bpy.ops.object.shade_smooth()

            bpy.context.object.data.extrude = 0.05

    # DRAW GPU SHADER LINES
    def draw_callback_3d(self, op, context):
        #PATH
        path = self.points.copy() #self.points.copy()

        if self.mouse_vert is not None:
            path.append()

        self.shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        # POINTS, LINES, TRIS, LINE_STRIP, LINE_LOOP,
        # TRI_STRIP, TRI_FAN, LINES_ADJ, TRIS_ADJ, LINE_STRIP_ADJ

        self.batch = batch_for_shader(self.shader, 'LINE_STRIP', {"pos": path})
        alpha_opacity = bpy.context.scene.draw_line_opacity
        line_width = bpy.context.scene.draw_line_width
        color = (1.0, 1.0, 1.0, alpha_opacity)
        if bpy.context.scene.hit_state == True:
            color = (0.1, 0.1, 1.0, alpha_opacity)
        elif bpy.context.scene.hit_state == False:
            color = (1.0, 0.1, 0.1, alpha_opacity)
        bgl.glLineWidth(line_width)
        self.shader.bind()
        self.shader.uniform_float("color", color)
        self.batch.draw(self.shader)
        
        # Fragment shaders for rounded points
        vshader = """
            uniform mat4 ModelViewProjectionMatrix;
            in vec3 pos;
            void main()
            {
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.999);
            }
        """

        fshader = """

            void main()
            {
                float r = 0.0, delta = 0.0, alpha = 0.0;
                vec2 cxy = 2.0 * gl_PointCoord - 1.0;
                r = dot(cxy, cxy);
                if (r > 1.0) {
                    discard;
                }
                gl_FragColor
                 = vec4(1.0, 1.0, 1.0, 1.0);
            }
        """

        glPointSize(7)

        bgl.glEnable(bgl.GL_BLEND)

        self.shader_points = GPUShader(vshader, fshader)

        self.batch_points = batch_for_shader(self.shader_points, 'POINTS', {"pos": path})
        self.shader_points.bind()
        self.batch_points.draw(self.shader_points)