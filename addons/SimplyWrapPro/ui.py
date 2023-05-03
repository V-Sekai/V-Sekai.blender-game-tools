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

from bpy.types import Panel
import bpy.utils.previews

custom_icons = None

class MO_PT_panel(bpy.types.Panel):
    bl_label = "Simply Wrap Pro - v1.3"
    bl_idname = "SIMPLYWRAP_PT_LAYOUT"
    bl_category = "Simply Addons"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        global custom_icons
        layout = self.layout
        selfob = bpy.context.active_object
        collision = False
        row = layout.row(align = True)
        if bpy.context.scene.modal_wrap_status == False:
            pass
        else:
            row.operator("object.reset_handlers", text="RESET", icon="FILE_REFRESH")
        
        # OVERLAY
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="Overlay".upper(), icon="OVERLAY")
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="", icon="RIGHTARROW")

        if context.active_object is not None:
            row.prop(context.object, "show_in_front", text="In Front", icon="FACESEL")
        row.prop(context.space_data.overlay,"show_wireframes", text="Wire", icon="VIEW_ORTHO")
        row.prop(context.space_data.overlay, "show_face_orientation",text="Face", icon="NORMALS_FACE")
        row.prop(context.space_data.shading, "show_xray", text="X-Ray", icon="XRAY")
        row = box.row()

        if "simply_curve" in bpy.data.objects or "SimplyWrapMesh" in bpy.data.objects:
            box = layout.box()
            row = box.row()
            row.alignment = "CENTER"
            row.label(text="Objects".upper(), icon="HIDE_OFF")
            row = box.row()

            if "simply_curve" in bpy.data.objects:
                row.label(text="", icon="RIGHTARROW")
                row.enabled = True
                op = row.operator("scene.show_curve_visibility",text="Curve", icon="CURVE_DATA")
                op.mode = "CURVE"

            if "SimplyWrapMesh" in bpy.data.objects:
                row.label(text="", icon="RIGHTARROW")
                row.enabled = True 
                op = row.operator("scene.show_curve_visibility",text="Mesh", icon="OUTLINER_OB_GREASEPENCIL")
                op.mode = "MESH"            

        if context.mode == "EDIT_MESH":
            box = layout.box()
            row = box.row()
            row.alignment = "CENTER"
            row.label(text="Close Endings".upper(), icon="AUTOMERGE_ON")
            row = box.row()
            row.label(text="", icon="SNAP_EDGE")
            op = row.operator("mesh.bridge_edge_loops", text="Bridge Edge Loops Endings")
            op.use_merge=False
            op.merge_factor=0.50
            op.number_cuts=3
            op.interpolation='SURFACE'
            op.smoothness=1.5
            op.profile_shape='SMOOTH'
            op.profile_shape_factor=0.49

            row = box.row()

        if context.active_object is not None:
            if context.active_object.type == "MESH" or context.active_object.type == "CURVE":
                #   CURVE UN/ HIDE &  MESH UN/ HIDE
                if context.mode == "EDIT_MESH":
                    # if "SimplyWrapMesh" in bpy.context.active_object.name or "wrapped" in bpy.context.active_object.name or "SimplyWrapCurveMesh" in bpy.context.active_object.name:
                    box = layout.box()
                    row = box.row()
                    row.alignment = "CENTER"
                    row.label(text="Pin Group".upper(), icon="PINNED")
                    row = box.row()
                    row.label(text="", icon="RESTRICT_SELECT_OFF")
                    row.operator("object.assign_pin_from_selected",text="Pin Selection")
                    row = box.row()
                    
                    row.alignment = "CENTER"
                    row.label(text="", icon="HIDE_OFF")
                    row.label(text="Show Intersection".upper())
                    row = box.row()
                    row.label(text="", icon="SELECT_INTERSECT")
                    row.operator("scene.show_intersected")
                        
                if context.mode == "OBJECT":
                    if selfob.modifiers:
                        for mod in selfob.modifiers:
                            if mod.type == 'COLLISION' and "SW" in mod.name:
                                collision = True
                            else:
                                collision = False

                    if "wrapped" not in bpy.context.active_object.name:
                        if "SimplyWrapMesh" in context.active_object.name or "SimplyWrapCurveMesh" in context.active_object.name:
                            box = layout.box()
                            row = box.row()
                            row.alignment = "CENTER"
                            row.label(text="Finish".upper(), icon="SHADERFX")
                            row = box.row()
                            row.label(text="", icon="RIGHTARROW")
                            row.scale_y = 3.0
                            row.operator("object.apply_modifiers_cloth_wrap", text="Apply Wrap", icon="CHECKMARK")
                            row = box.row()

                    if collision == False:
                        if 'simply_curve' not in context.active_object.name:
                            if "SimplyWrapMesh" in bpy.data.objects or "wrapped" in bpy.data.objects or "SimplyWrapCurveMesh" in bpy.data.objects:
                                pass
                            else:
                                box = layout.box()
                                row = box.row()
                                row.alignment="CENTER"
                                row.label(icon="ERROR", text="Starting".upper())
                                row = box.row()

                                row.label(icon="RIGHTARROW", text="")
                                row.scale_y = 2.0
                                row.operator("object.add_collision_to_target_obj",text="Select Object for Wrapping!", icon="MOD_PHYSICS")
                                row = box.row()

                    elif collision == True:
                        if bpy.context.scene.modal_wrap_status == True:
                            text = "Running..."
                            if context.scene.hit_state == True:
                                icon_orientation = custom_icons["icon_front"].icon_id
                                textOrientationSide = "Front"
                            elif context.scene.hit_state == False:
                                textOrientationSide = "Back"
                                icon_orientation = custom_icons["icon_back"].icon_id

                            box = layout.box()
                            row = box.row()
                            row.alignment ="CENTER"
                            textOrientation = "Drawing - " + textOrientationSide
                            row.label(text=textOrientation,
                                      icon_value=icon_orientation)
                            row = box.row()

                            # LOCK ORIENTATION
                            iconOrientationLock = "UNLOCKED"
                            if bpy.context.scene.lock_draw_orientation == True:
                                iconOrientationLock = "LOCKED"
                            if bpy.context.scene.lock_draw_orientation == False:
                                iconOrientationLock = "UNLOCKED"

                            row.scale_y = 2.0
                            row.label(text="", icon="RIGHTARROW")
                            textSide = "Switch"

                            row.prop(context.scene, "hit_state",text="Switch", icon="FILE_REFRESH")
                            row.prop(context.scene, "lock_draw_orientation",text="Lock", icon=iconOrientationLock)

                            row = box.row()
                            row.label(text="", icon="MOD_THICKNESS")
                            row.prop(context.scene, "draw_line_width",text="Line Width")
                            row = box.row()
                            row.label(text="", icon="CON_FOLLOWPATH")
                            row.prop(context.scene, "path_smoothing",text="Path Smoothing", expand=True)

                            # POINT COUNT RESOLUTION
                            icon_pointCount = custom_icons["icon_point_count"].icon_id

                            row = box.row()
                            row.label(text="", icon_value=icon_pointCount)
                            row.prop(context.scene, "point_count",text="Draw Point Count", expand=True)

                        elif bpy.context.scene.modal_wrap_status == False:
                            text = "Start Wrapping!"
                            box = layout.box()
                            row = box.row()
                            row.alignment="CENTER"
                            row.label(text="Wrap it!".upper(), icon="TRACKING")
                            row = box.row()
                            row.scale_y = 2.0
                            row.label(text="", icon_value=custom_icons["icon_wrap"].icon_id)
                            row.operator("object.modal_wrap", text=text)
                            # row.operator("scene.reset_modal", icon="FILE_REFRESH", text="")
                            row = box.row()

                            # START DRAWING ORIENTATION
                            box = layout.box()
                            row = box.row()
                            row.alignment = "CENTER"
                            row.label(text="Drawing Settings".upper(),icon="SETTINGS")
                            row = box.row()
                            row.scale_y = 2.0
                            if context.scene.hit_state == True:
                                icon_orientation = custom_icons["icon_front"].icon_id
                                text = "Front"
                            elif context.scene.hit_state == False:
                                icon_orientation = custom_icons["icon_back"].icon_id
                                text = "Back"

                            row.label(text="",icon_value=icon_orientation)

                            # LOCK ORIENTATION
                            iconOrientationLock = "UNLOCKED"
                            if bpy.context.scene.lock_draw_orientation == True:
                                iconOrientationLock = "LOCKED"
                            if bpy.context.scene.lock_draw_orientation == False:
                                iconOrientationLock = "UNLOCKED"

                            row.prop(context.scene, "hit_state",text=text, icon="BLANK1")
                            row.prop(context.scene, "lock_draw_orientation",text="Lock", icon=iconOrientationLock)

                            # POINT COUNT RESOLUTION
                            icon_pointCount = custom_icons["icon_point_count"].icon_id
                            row = box.row()
                            row.label(text="", icon_value=icon_pointCount)

                            row.prop(context.scene, "point_count",
                                     text="Point Count", expand=True)
                            row = box.row()
                            
                            row.scale_y = 2.0
                            row.label(text="", icon="MOD_SHRINKWRAP")
                            row.prop(context.scene, "shrink_curve",text="Shrink Curve after Drawing", expand=True, icon="BLANK1")
                            row = box.row()

                            row.label(text="", icon="OBJECT_DATA")
                            row.prop(context.scene, "offset_value",text="Surface Offset", expand=True)

                            row.label(text="", icon="CON_FOLLOWPATH")
                            row.prop(context.scene, "path_smoothing",text="Path Smooth", expand=True)                            
                            row = box.row()
                                     
                            # COLLISION OBJECT SETTINGS
                            box = layout.box()
                            row = box.row()
                            row.alignment = "CENTER"
                            row.label(text="Object Collision".upper(), icon="IMPORT")
                            row = box.row()
                            row.label(text="", icon="MOD_DECIM")
                            row.prop(context.active_object.modifiers["SWCollisionDecimate"], "ratio", text="Decimate")
                            row.prop(context.active_object.modifiers["SWCollisionDecimate"], "show_viewport", text="")
                            row.operator("object.remove_collision_modifier", text="", icon="TRASH")

                            row = box.row()
                            row.label(text="", icon="MOD_PHYSICS")
                            row.prop(context.active_object.modifiers["SWCollision"].settings, "cloth_friction", text="Friction")
                            row = box.row()
                            row.alignment= "CENTER"
                            row = box.row()
                            row.label(text="", icon="FULLSCREEN_EXIT")
                            row.prop(context.active_object.modifiers["SWCollision"].settings, "thickness_inner", text="Thick Inner", slider=True)

                            row.label(text="", icon="FULLSCREEN_ENTER")
                            row.prop(context.active_object.modifiers["SWCollision"].settings, "thickness_outer", text="Thick Outer", slider=True)
                            row = box.row()

                    if "SimplyWrapMesh" not in context.active_object.name and "simply_curve" in bpy.data.objects and "wrap" not in context.active_object.name and "CURVE" not in context.active_object.type:
                        box = layout.box()
                        row = box.row()
                        row.alignment = "CENTER"
                        row.label(text="Custom Object".upper(), icon="REC")
                        row = box.row()
                        row.label(text="", icon="RIGHTARROW")
                        if "Array" not in context.active_object.modifiers:
                            row.scale_y = 2.0
                            row.operator("object.add_custom_to_curve",text="Add selected Object to Wrap", icon="PARTICLE_POINT")
                        else:
                            row.prop(context.active_object.modifiers["Array"], "relative_offset_displace", text="Array")
                    

            if context.mode == "OBJECT":
                if "wrapped" in bpy.context.active_object.name:
                    box = layout.box()
                    row = box.row()
                    row.alignment = "CENTER"
                    row.label(text="Clean Up Endings".upper(), icon="SHADERFX")
                    row = box.row()
                    row.label(text="", icon="DRIVER_DISTANCE")
                    row.prop(context.scene, "shorten_wrap_ends",text="Shorten Ending", icon="BLANK1")
                    row = box.row()

                for mod in bpy.context.active_object.modifiers:
                    if "CLOTH" in mod.type:
                        # ANIMATION
                        box = layout.box()
                        box.ui_units_y = 5.5
                        row = box.row()
                        row.alignment = "CENTER"

                        row.label(text="Animation".upper(), icon="RENDER_ANIMATION")
                        row = box.row()
                        row.label(text="", icon="MOD_TIME")
                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].settings, "time_scale", text="Speed", slider=True)

                        row.label(text="", icon="IMPORT")
                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].settings.effector_weights,"gravity", text="Gravity", slider=True)

                        row = box.row()
                        row.label(text="", icon="RIGHTARROW")
                        row.scale_y = 2.0
                        iconPlay = custom_icons["icon_play"].icon_id
                        textPlay = "Play"

                        if bpy.context.screen.is_animation_playing == True:
                            iconPlay = custom_icons["icon_pause"].icon_id
                            textPlay = "Pause"
                        if bpy.context.screen.is_animation_playing == False:
                            iconPlay = custom_icons["icon_play"].icon_id
                            textPlay = "Play"

                        op = row.operator("object.play_stop",text=textPlay, icon_value=iconPlay)
                        op.state = "PLAY"

                        op = row.operator("object.play_stop", text="Stop", icon_value=custom_icons["icon_stop"].icon_id)
                        op.state = "STOP"
                        row = box.row()

                        box = layout.box()
                        row = box.row()
                        row.alignment = "CENTER"
                        row.label(text="Cloth".upper(), icon="MOD_CLOTH")

                        row = box.row()
                        row.label(text="", icon="MOD_VERTEX_WEIGHT")
                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].settings, "mass", text="Weight", icon="BLANK1")

                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].settings, "quality", text="Quality Steps", icon="BLANK1")
                        row = box.row()
                        row.label(text="", icon="FULLSCREEN_EXIT")

                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].settings,"shrink_min", text="Shrink", icon="BLANK1", slider=True)
                        row.operator("object.reset_shrink_keyframe_animation", text="", icon="RENDER_ANIMATION")
                        row.operator("anim.keyframe_clear_v3d",text="", icon="TRASH")
                        row = box.row()

                        box = layout.box()
                        row = box.row()
                        row.alignment= "CENTER"
                        row.label(text="Collision".upper(), icon="MOD_BOOLEAN")

                        row = box.row()
                        row.label(text="", icon="DRIVER_DISTANCE")
                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].collision_settings,"distance_min", text="Distance", slider=True)

                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].collision_settings,"collision_quality", text="Quality", icon="BLANK1", slider=True)
                        row = box.row()

                        row.label(text="", icon="RIGHTARROW")
                        row.scale_y = 2.0
                        row.prop(context.active_object.modifiers["SimplyWrapCloth"].collision_settings,"use_self_collision", text="Self Collision", icon="MOD_MASK")
                        if bpy.context.object.modifiers["SimplyWrapCloth"].collision_settings.use_self_collision == True:
                            row = box.row()
                            row.label(text="", icon="UV_ISLANDSEL")
                            row.prop(context.active_object.modifiers["SimplyWrapCloth"].collision_settings, "self_friction", text="Self Friction", slider=True)
                            row = box.row()
                            row.label(text="", icon="DRIVER_DISTANCE")
                            row.prop(context.active_object.modifiers["SimplyWrapCloth"].collision_settings, "self_distance_min", text="Self Distance", slider=True)
                            row = box.row()

                    if mod.type == 'SOLIDIFY' and "SimplyWrap" in mod.name:
                        box = layout.box()
                        row = box.row()
                        row.alignment = "CENTER"
                        row.label(text="Thickness".upper(), icon="MOD_SOLIDIFY")
                        row = box.row()

                        row.label(text="", icon="MOD_SKIN")
                        row.prop(mod, "thickness", text="Thickness")
                        row.prop(context.active_object.modifiers["SimplyWrapSolidify"], "show_viewport", text="")
                        row.prop(context.active_object.modifiers["SimplyWrapSolidify"], "show_render", text="")

                        row = box.row()
                        row.label(text="", icon="RIGHTARROW")
                        row.prop(context.active_object.modifiers["SimplyWrapSolidify"], "use_rim", icon="FACESEL")
                        row.prop(context.active_object.modifiers["SimplyWrapSolidify"], "use_flip_normals", icon="NORMALS_FACE")

                    if mod.type == "SMOOTH" and "SimplyWrap" in mod.name:
                        row = box.row()
                        row.label(text="", icon="MOD_SMOOTH")
                        row.prop(context.active_object.modifiers["SimplyWrapSmooth"], "factor", text="Width")
                        row.prop(context.active_object.modifiers["SimplyWrapSmooth"], "iterations", text="")
                        row = box.row()

                if bpy.context.active_object.type == "CURVE":
                    box = layout.box()
                    row = box.row()
                    row.alignment= "CENTER"
                    row.label(text="Curve Settings".upper(), icon="CURVE_DATA")
                    row = box.row()
                    row.label(text="", icon="RIGHTARROW")
                    row.scale_y = 2.0
                    row.operator("object.shade_smooth",text="Shade Smooth", icon="ANTIALIASED")
                    row.operator("object.shade_flat", text="Shade Flat", icon="ALIASED")
                    row = box.row()
                    curve = bpy.context.active_object.data
                    shrink = False
                    for mod in bpy.context.active_object.modifiers:
                        if mod.type == 'SHRINKWRAP':
                            row.label(text="", icon="GIZMO")
                            row.prop(mod, "offset", text="Offset")
                            row.prop(mod, "show_in_editmode", text="")
                            row.prop(mod, "show_viewport", text="")
                            row.prop(mod, "show_render", text="")
                            shrink = True
                            break

                    if shrink == False:
                        row.label(text="", icon="GIZMO")
                        row.prop(curve, "offset", text="Offset")

                    row = box.row()
                    row.label(text="", icon="MOD_BOOLEAN")
                    if context.object.data.extrude == 0.0:
                        row.alert = True
                        row.prop(curve, "extrude", text="Extrude")
                    elif context.object.data.extrude > 0.0:
                        row.alert = False
                        row.prop(curve, "extrude", text="Extrude")
                    row.alert = False
                    row.prop(curve, "bevel_depth", text="Depth")

                    row = box.row()
                    row.label(text="", icon="RNA")
                    row.prop(curve, "twist_smooth", text="Twist Smooth")

                    box = layout.box()
                    row = box.row()
                    row.alignment = "CENTER"
                    row.label(text="Convert to Mesh".upper(), icon="STROKE")

                    if context.object.data.extrude > 0.0:
                        row.enabled = True
                        row = box.row()
                        row.scale_y = 2
                        row.alert = False
                        row.label(text="", icon="OUTLINER_OB_CURVE")
                        row.operator("curve.generate_wrap_from_curve",text="Generate Mesh Wrap from Curve")
                    elif context.object.data.extrude == 0.0:
                        row = box.row()

                        row.enabled = False
                        row.scale_y = 2
                        row.alert = True
                        
                        row.label(text="", icon="OUTLINER_OB_CURVE")
                        row.operator("curve.generate_wrap_from_curve",text="Generate Mesh Wrap from Curve")

        if bpy.context.scene.info_box == True:
            box = layout.box()
            row = box.row()
            row.label(text="Info Section", icon="QUESTION")
            row = box.row()

            row.label(text="", icon_value=custom_icons["icon_front"].icon_id)
            row.emboss = "PULLDOWN_MENU"
            row.label(text="Side - Starting side during drawing wrap")
            row = box.row()

            row.label(text="", icon="MOD_DECIM")
            row.emboss = "PULLDOWN_MENU"
            row.label(text="Decimate - Reduces polycount of Collision Mesh for better Performance")
            row = box.row()

            row.label(text="", icon="DRIVER_DISTANCE")
            row.emboss = "PULLDOWN_MENU"
            row.label(text="Collision Distance - Set lower value for tighter wrap")
            row = box.row()

            row.label(text="", icon="SHADERFX")
            row.emboss = "PULLDOWN_MENU"
            row.label(text="Better Results - Start drawing on Collision Mesh")
            row = box.row()

            row.label(text="", icon="MOD_SHRINKWRAP")
            row.emboss = "PULLDOWN_MENU"
            row.label(text="Shrink Curve by Generation - Shrink Wrap to Object but could destroy Overlapping")

            pass

def shorten_endings(self, context):
    if context.mode == "OBJECT":
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.cleanup_endings()
        bpy.ops.object.editmode_toggle()


def registerIcon():
	import bpy.utils.previews
	global custom_icons

	custom_icons = bpy.utils.previews.new()
	custom_path = bpy.utils.script_path_pref()
	addons_path = bpy.utils.user_resource(resource_type="SCRIPTS", path="addons")

	if custom_path is not None:
		addons_path = os.path.join(custom_path, "addons")
	script_path = os.path.join(addons_path, "SimplyWrapPro")
	icons_dir = os.path.join(script_path, "icons")

	custom_icons.load("icon_front", os.path.join(icons_dir, "icon_front.png"), 'IMAGE')
	custom_icons.load("icon_back", os.path.join(icons_dir, "icon_back.png"), 'IMAGE')
	custom_icons.load("icon_wrap", os.path.join(icons_dir, "icon_wrap.png"), 'IMAGE')
	custom_icons.load("icon_point_count", os.path.join(icons_dir, "icon_point_count.png"), 'IMAGE')
	custom_icons.load("icon_play", os.path.join(icons_dir, "icon_play.png"), 'IMAGE')
	custom_icons.load("icon_stop", os.path.join(icons_dir, "icon_stop.png"), 'IMAGE')
	custom_icons.load("icon_pause", os.path.join(icons_dir, "icon_pause.png"), 'IMAGE')


def unregisterIcon():
	global custom_icons