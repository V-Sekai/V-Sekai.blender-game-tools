import io
import time
from contextlib import redirect_stdout
import bpy
from bpy.props import BoolProperty, IntProperty, FloatProperty
from mathutils import Vector

from ..core.modifier_utils import add_faceit_armature_modifier, get_faceit_armature_modifier, set_bake_modifier_item

from ..core import faceit_utils as futils
from ..core import mesh_utils, shape_key_utils
from ..core import vgroup_utils as vg_utils
from . import bind_utils


class FACEIT_OT_SmartBind(bpy.types.Operator):
    '''Bind main objects (Face, Eyes, Teeth, Tongue)'''
    bl_idname = "faceit.smart_bind"
    bl_label = "Bind"
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    show_advanced_settings: BoolProperty(
        name="Show Advanced Options",
        default=False,
    )
    bind_scale_objects: BoolProperty(
        name="Scale Geometry",
        description="Temporarilly scales the geometry for Binding. Use if Auto Weights fails.",
        default=True
    )
    bind_scale_factor: IntProperty(
        name="Scale Factor",
        description="Factor to scale by. Tweak this if your binding fails",
        default=100,
        max=1000,
        min=1,
    )
    smart_weights: BoolProperty(
        name="Smart Weights",
        description="Improves weights for most characters, by detecting rigid skull/body vertices and assigning them to DEF-face group",
        default=True)
    smooth_main_edges: BoolProperty(
        name="Smooth Main borders/edge",
        description="Ensures a smooth transition between face and body/rigid geometry.",
        default=True
    )
    main_smooth_factor: FloatProperty(
        name="Smooth Factor",
        description="Factor to smooth by.",
        default=0.5,
        min=0.0,
        max=1.0,
    )
    main_smooth_steps: IntProperty(
        name="Smooth Steps",
        description="Number of smoothing steps (Iterations).",
        default=10,
        min=1,
        max=10000
    )
    main_smooth_expand: FloatProperty(
        name="Smooth Expand",
        description="Expand/contract weights during smoothing",
        default=0.1,
        min=-1.0,
        max=1.0,
    )
    weight_eyes: BoolProperty(
        name="Eyes",
        description="Overwrite Faceit Vertex Groups with specific bone weights (Eyes)",
        default=True
    )
    weight_teeth: BoolProperty(
        name="Teeth",
        description="Overwrite Faceit Vertex Groups with specific bone weights (Teeth)",
        default=True
    )
    weight_tongue: BoolProperty(
        name="Tongue",
        description="Auto weight the tongue geometry separately.",
        default=True
    )
    transfer_weights: BoolProperty(
        name="Transfer Weights",
        description="Transfer the Main Weights to hair/secondary Geometry",
        default=True
    )
    tranfer_to_hair_only: BoolProperty(
        name="Transfer to Hair Only",
        description="Automatically find hair geometry. All geometry that is not assigned to Faceit vertex groups.",
        default=False,
    )
    clean_eyelashes_weights: BoolProperty(
        name="Clean Eyelashes Weights",
        description="Remove all non-lid deform groups from the eyelashes gemometry. Only available if the eyelashes have been defined in setup.",
        default=True,)
    remove_rigid_weights: BoolProperty(
        name="Clear Rigid Geometry",
        description="Removes all weights from geometry assigned to the faceit_rigid group.",
        default=True
    )
    keep_split_objects: BoolProperty(
        name="Keep Split Objects",
        description="Keep the Split objects for inspection. This can be useful when binding fails.",
        default=False
    )
    smooth_bind: BoolProperty(
        name="Apply Smoothing",
        description="Applies automatic weight-smoothing after binding. Affects all deform bones.",
        default=True
    )
    smooth_factor: FloatProperty(
        name="Smooth Factor",
        description="Factor to smooth by.",
        default=0.5,
        min=0.0,
        max=1.0,
    )
    smooth_steps: IntProperty(
        name="Smooth Steps",
        description="Number of smoothing steps (Iterations).",
        default=1,
        min=1,
        max=10000
    )
    smooth_expand: FloatProperty(
        name="Smooth Expand",
        description="Expand/contract weights during smoothing",
        default=0.0,
        min=-1.0,
        max=1.0,
    )
    smooth_expand_eyelashes: BoolProperty(
        name="Smooth Expand Eyelashes",
        description="Smooth the eyelashes in an extra pass.",
        default=True,
    )
    eyelashes_smooth_factor: FloatProperty(
        name="Smooth Factor",
        description="Factor to smooth by.",
        default=0.5,
        min=0.0,
        max=1.0,
    )
    eyelashes_smooth_steps: IntProperty(
        name="Smooth Steps",
        description="Number of smoothing steps (Iterations).",
        default=2,
        min=1,
        max=10000
    )
    eyelashes_smooth_expand: FloatProperty(
        name="Smooth Expand",
        description="Expand/contract weights during smoothing",
        default=1.0,
        min=-1.0,
        max=1.0,
    )
    remove_old_faceit_weights: BoolProperty(
        name="Remove Old Faceit Weights",
        description="Removes all weights associated with the FaceitRig before rebinding.",
        default=True
    )
    make_single_user: BoolProperty(
        name="Make Single User",
        description="Makes single user copy before binding. Otherwise Binding will likely fail.",
        default=True
    )

    found_faceit_eyelashes_grp = False
    found_faceit_eyes_grp = False
    found_faceit_teeth_grp = False
    found_faceit_tongue_grp = False

    @classmethod
    def poll(cls, context):
        rig = futils.get_faceit_armature(force_original=True)
        if rig and context.scene.faceit_face_objects:
            if rig.hide_viewport is False and context.mode == 'OBJECT':
                return True

    def invoke(self, context, event):
        objects = futils.get_faceit_objects_list()
        self.found_faceit_eyelashes_grp = bool(vg_utils.get_objects_with_vertex_group(
            "faceit_eyelashes", objects=objects, get_all=False))
        if not self.found_faceit_eyelashes_grp:
            self.smooth_expand_eyelashes = self.clean_eyelashes_weights = False
        # teeth_grps = ("faceit_upper_teeth", "faceit_lower_teeth")
        # for grp in teeth_grps:
        #     self.found_faceit_teeth_grp = bool(vg_utils.get_objects_with_vertex_group(
        #         grp, objects=objects, get_all=False))
        # if not self.found_faceit_teeth_grp:
        #     self.weight_teeth = False
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        col_bind = layout.column()
        row = col_bind.row(align=True)
        row.prop(self, "bind_scale_objects", icon='EMPTY_DATA')
        if self.bind_scale_objects:
            row.prop(self, "bind_scale_factor")
        row = col_bind.row()
        row.prop(self, "show_advanced_settings", icon="COLLAPSEMENU")
        if self.show_advanced_settings:
            row = col_bind.row()
            row.prop(self, "smart_weights")
            if self.smart_weights:
                row = col_bind.row()
                row.prop(self, "smooth_main_edges")
                if self.smooth_main_edges:
                    col_bind.use_property_split = True
                    row = col_bind.row()
                    row.prop(self, "main_smooth_factor")
                    row = col_bind.row()
                    row.prop(self, "main_smooth_steps")
                    row = col_bind.row()
                    row.prop(self, "main_smooth_expand")
                    col_bind.use_property_split = False
                    row = col_bind.row()
            row = col_bind.row()
            row.prop(self, "remove_old_faceit_weights")
            row.prop(self, "remove_rigid_weights")
            row = col_bind.row()
            row.prop(self, "weight_eyes")
            row.prop(self, "weight_teeth")
            row = col_bind.row()
            row.prop(self, "weight_tongue")
            row = col_bind.row()
            row.label(text="Note: Assign the Groups in Setup.")
            row = col_bind.row()
            row.prop(self, "smooth_bind")
            if self.smooth_bind:
                col_bind.use_property_split = True
                row = col_bind.row()
                row.prop(self, "smooth_factor")
                row = col_bind.row()
                row.prop(self, "smooth_steps")
                row = col_bind.row()
                row.prop(self, "smooth_expand")
                col_bind.use_property_split = False
            row = col_bind.row()
            row.prop(self, "transfer_weights")
            if self.transfer_weights:
                row.prop(self, "tranfer_to_hair_only")
                row = col_bind.row()
                row.prop(self, "clean_eyelashes_weights")
                row.prop(self, "smooth_expand_eyelashes")
                if not self.found_faceit_eyelashes_grp:
                    row.enabled = False
                    row.active = False
                    row = col_bind.row()
                    row.label(text="No Eyelashes Found.")

                if self.smooth_expand_eyelashes:
                    col_bind.use_property_split = True
                    row = col_bind.row()
                    row.prop(self, "eyelashes_smooth_factor")
                    row = col_bind.row()
                    row.prop(self, "eyelashes_smooth_steps")
                    row = col_bind.row()
                    row.prop(self, "eyelashes_smooth_expand")
                    col_bind.use_property_split = False
                    row = col_bind.row()
            row = col_bind.row()
            row.prop(self, "make_single_user")
            row.prop(self, "keep_split_objects")

    def execute(self, context):
        scene = context.scene
        hide_modifiers = [
            'ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE', 'EDGE_SPLIT', 'MASK', 'MIRROR', 'MULTIRES', 'REMESH',
            'SCREW', 'SKIN', 'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'WIREFRAME']
        # --------------- RELEVANT OBJECTS -------------------
        start_time = time.time()
        faceit_objects = futils.get_faceit_objects_list()
        if not faceit_objects:
            self.report({'ERROR'}, "No objects registered! Complete Setup")
            return {'FINISHED'}
        lm_obj = futils.get_object("facial_landmarks")
        if not lm_obj:
            self.report({'ERROR'}, "Faceit landmarks not found!")
            return {'FINISHED'}
        rig = futils.get_faceit_armature()
        if not rig:
            self.report({'ERROR'}, "Faceit rig not found!")
            return {'FINISHED'}
        # --------------- CHECK MAIN GROUP/OBJECT ---------------
        face_obj = futils.get_main_faceit_object()
        if not face_obj:
            self.report(
                {'ERROR'},
                "Please assign the Main group to the face before Binding.")
            return {"CANCELLED"}
        # --------------- SCENE SETTINGS -------------------
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        use_auto_normalize = scene.tool_settings.use_auto_normalize
        scene.tool_settings.use_auto_normalize = False
        transform_orientation = scene.transform_orientation_slots[0].type
        scene.transform_orientation_slots[0].type = 'GLOBAL'
        mesh_select_mode = scene.tool_settings.mesh_select_mode[:]
        scene.tool_settings.mesh_select_mode = (True, True, True)
        scene.tool_settings.use_keyframe_insert_auto = False
        pivot_setting = scene.tool_settings.transform_pivot_point
        simplify_value = scene.render.use_simplify
        simplify_subd = scene.render.simplify_subdivision
        scene.render.use_simplify = True
        scene.render.simplify_subdivision = 0

        futils.set_hide_obj(lm_obj, False)
        futils.set_hide_obj(rig, False)
        rig.data.pose_position = 'REST'
        # enable all armature layers
        layer_state = rig.data.layers[:]
        for i in range(len(rig.data.layers)):
            rig.data.layers[i] = True
        # --------------- OBJECT & ARMATURE SETTINGS -------------------
        # | - Unhide Objects
        # | - Hide Generators (Modifier)
        # | - Set Mirror Settings (asymmetry or not)
        # -------------------------------------------------------
        obj_mod_show_dict = {}
        obj_mod_drivers = {}
        obj_settings = {}
        obj_sk_dict = {}
        for obj in faceit_objects:

            obj_settings[obj.name] = {
                "topology_mirror": obj.data.use_mirror_topology,
                "lock_location": obj.lock_location[:],
                "lock_rotation": obj.lock_rotation[:],
                "lock_scale": obj.lock_scale[:],
            }
            obj.lock_scale[:] = (False,) * 3
            obj.lock_location[:] = (False,) * 3
            obj.lock_rotation[:] = (False,) * 3
            obj.data.use_mirror_topology = False
            obj.data.use_mirror_x = False if scene.faceit_asymmetric else True

            if obj.data.users > 1:
                if self.make_single_user:
                    obj.data = obj.data.copy()
                    print(f"Making Single user copy of objects {obj.name} data")
                else:
                    self.report(
                        {'WARNING'},
                        f"The object {obj.name} has multiple users. Check Make Single User in Bind Settings if binding fails.")

            futils.set_hidden_state_object(obj, False, False)
            futils.clear_object_selection()
            futils.set_active_object(obj.name)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.reveal()
            bpy.ops.object.mode_set(mode='OBJECT')

            other_rigs = []
            # Hide Modifiers and mute drivers if necessary
            for mod in obj.modifiers:
                if mod.type in hide_modifiers:
                    if obj.animation_data:
                        for dr in obj.animation_data.drivers:
                            # If it's muted anyways, continue
                            if dr.mute:
                                continue
                            if "modifiers" in dr.data_path:
                                try:
                                    obj_mod_drivers[obj.name].append(dr.data_path)
                                except KeyError:
                                    obj_mod_drivers[obj.name] = [dr.data_path]
                                dr.mute = True
                    try:
                        obj_mod_show_dict[obj.name][mod.name] = mod.show_viewport
                    except KeyError:
                        obj_mod_show_dict[obj.name] = {mod.name: mod.show_viewport}
                    mod.show_viewport = False

            # Remove all FaceitRig vertex groups
            if self.remove_old_faceit_weights:
                other_deform_groups = []
                if other_rigs:
                    for o_rig in other_rigs:
                        other_deform_groups.extend(vg_utils.get_deform_bones_from_armature(o_rig))
                # Just get current vertex groups
                deform_groups = vg_utils.get_deform_bones_from_armature(rig)
                vertex_group_intersect = (set(deform_groups).intersection(set(other_deform_groups)))
                if vertex_group_intersect:
                    self.report(
                        {'WARNING'},
                        "There seems to be another rig with similar bone names: {}. This can lead to weight conflicts. Faceit will add the influence.".
                        format(vertex_group_intersect))
                for grp in obj.vertex_groups:
                    if grp.name in deform_groups:
                        if grp.name not in other_deform_groups:
                            obj.vertex_groups.remove(grp)

            if shape_key_utils.has_shape_keys(obj):
                for sk in obj.data.shape_keys.key_blocks:
                    if sk.name.startswith('faceit_cc_'):
                        sk.mute = True
                # --------------- DUPLICATE OBJECT(S) -------------------
                # | - Preserve Data (Vertex Groups + Shape Keys)
                # -------------------------------------------------------
        dup_objects_dict = {}
        dup_face_objects = []
        obj_data_dict = {}
        dg = bpy.context.evaluated_depsgraph_get()
        futils.clear_object_selection()
        for obj in faceit_objects:
            eval_mesh_data = shape_key_utils.get_mesh_data(obj, dg)
            # Create static duplicates of all meshes for binding.
            obj_eval = obj.evaluated_get(dg)
            me = bpy.data.meshes.new_from_object(obj_eval)
            dup_obj = bpy.data.objects.new(obj.name, me)
            dup_obj.matrix_world = obj.matrix_world
            dup_objects_dict[obj] = dup_obj
            dup_face_objects.append(dup_obj)
            scene.collection.objects.link(dup_obj)
            dup_obj.select_set(state=True)

            # Original Object: Store Shape Keys + delete (for data transfer to work!)
            if shape_key_utils.has_shape_keys(obj):
                sk_dict = shape_key_utils.store_shape_keys(obj)
                sk_action = None
                if obj.data.shape_keys.animation_data:
                    sk_action = obj.data.shape_keys.animation_data.action
                obj_sk_dict[obj] = {
                    "sk_dict": sk_dict,
                    "sk_action": sk_action,
                }
                shape_key_utils.remove_all_sk_apply_basis(obj, apply_basis=True)

            basis_data = shape_key_utils.get_mesh_data(obj, evaluated=False)
            obj_data_dict[obj.name] = [basis_data, eval_mesh_data]
            # Remove all vertex groups from duplicates, except for faceitgroups
            for grp in dup_obj.vertex_groups:
                if "faceit_" not in grp.name:
                    dup_obj.vertex_groups.remove(grp)
        # Remove parent - keep transform! Parent objects with Transforms can mess up the process!
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        # --------------- SCALE OBJECT(S) -------------------
        # | - Scale armature, bind objects, landmarks to avoid Auto Weight error. Known Issue in Blender
        # -------------------------------------------------------
        scene.cursor.location = Vector()
        scene.tool_settings.transform_pivot_point = 'CURSOR'

        if self.bind_scale_objects:
            scale_factor = self.bind_scale_factor
            bind_utils.scale_bind_objects(factor=scale_factor, objects=[rig, *dup_face_objects, lm_obj])
        # --------------- MAIN BINDING PROCESS -------------------
        # | - Bind (main geo) +
        # | - Data Transfer (hair, beard,brows etc.) +
        # | - Secondary Assigns (eyes, teeth, tongue)
        # -------------------------------------------------------
        bind_success = self._bind(
            context,
            bind_objects=dup_face_objects,
            rig=rig,
            lm_obj=lm_obj,
        )
        # --------------- RESTORE SCALE(S) -------------------
        scene.cursor.location = Vector()
        scene.tool_settings.transform_pivot_point = 'CURSOR'

        if self.bind_scale_objects:
            bind_utils.scale_bind_objects(factor=scale_factor, objects=[rig, *dup_face_objects, lm_obj], reverse=True)
            rig.scale = Vector((1,) * 3)
        # --------------- RESTORE OBJECT DATA -------------------
        # | - Data Transfer the original data
        # -------------------------------------------------------
        for obj, dup_obj in dup_objects_dict.items():
            # Bring original mesh to evaluated shape
            obj.data.vertices.foreach_set('co', obj_data_dict[obj.name][1].ravel())
            dg.update()
            bind_utils.data_transfer_vertex_groups(obj_from=dup_obj, obj_to=obj, apply=True, method='NEAREST')
            dg.update()
            # Bring original mesh back to basis shape
            obj.data.vertices.foreach_set('co', obj_data_dict[obj.name][0].ravel())
            bpy.data.objects.remove(dup_obj, do_unlink=True)
            futils.clear_object_selection()
            futils.set_active_object(obj.name)
            # --------------- OBJECT & ARMATURE SETTINGS -------------------
            # | - Unhide Objects
            # | - Restore Modifier States
            # | - Restore Shape Keys
            # --------------------------------------------------------------
            obj.data.use_mirror_topology = obj_settings[obj.name]["topology_mirror"]
            obj.lock_location = obj_settings[obj.name]["lock_location"]
            obj.lock_rotation = obj_settings[obj.name]["lock_rotation"]
            obj.lock_scale = obj_settings[obj.name]["lock_scale"]
            dr_dict = obj_mod_drivers.get(obj.name)
            if dr_dict:
                for dr_dp in dr_dict:
                    if obj.animation_data:
                        dr = obj.animation_data.drivers.find(dr_dp)
                        if dr:
                            dr.mute = False

            show_mod_dict = obj_mod_show_dict.get(obj.name)
            if show_mod_dict:
                for mod_name, show_value in show_mod_dict.items():
                    mod = obj.modifiers.get(mod_name)
                    if mod:
                        mod.show_viewport = show_value
            sk_data_dict = obj_sk_dict.get(obj)
            if sk_data_dict:
                sk_dict = sk_data_dict["sk_dict"]
                sk_action = sk_data_dict["sk_action"]
                shape_key_utils.apply_stored_shape_keys(obj, sk_dict, apply_drivers=True)
                for sk in obj.data.shape_keys.key_blocks:
                    if sk.name.startswith('faceit_cc_'):
                        sk.mute = False
            if shape_key_utils.has_shape_keys(obj):
                if sk_action:
                    if not obj.data.shape_keys.animation_data:
                        obj.data.shape_keys.animation_data_create()
                    obj.data.shape_keys.animation_data.action = sk_action

            # ----------------- FACEIT MODIFIER --------------------------
            # | - Check for bind groups and ensure the modifier is applied
            # -------------------------------------------------------------
            deform_groups = vg_utils.get_deform_bones_from_armature(rig)
            if not any([grp in obj.vertex_groups for grp in deform_groups]):
                continue
            add_faceit_armature_modifier(obj, rig)
        # --------------- RESTORE SETTINGS -------------------
        rig.data.pose_position = 'POSE'
        rig.data.layers = layer_state[:]
        futils.set_hidden_state_object(lm_obj, True, True)
        scene.tool_settings.transform_pivot_point = pivot_setting
        context.scene.tool_settings.use_auto_normalize = use_auto_normalize
        scene.transform_orientation_slots[0].type = transform_orientation
        context.space_data.overlay.show_relationship_lines = False
        scene.tool_settings.use_keyframe_insert_auto = auto_key
        scene.render.use_simplify = simplify_value
        scene.render.simplify_subdivision = simplify_subd
        scene.tool_settings.mesh_select_mode = mesh_select_mode
        scene.tool_settings.transform_pivot_point = 'INDIVIDUAL_ORIGINS'
        futils.clear_object_selection()
        futils.set_active_object(rig.name)
        bpy.ops.outliner.orphans_purge()
        if bind_success:
            self.report({'INFO'}, "Faceit Binding Successful")
            print("Bound in {}".format(round(time.time() - start_time, 2)))
        else:
            self.report({'ERROR'}, "Faceit Binding Failed. See Console for more info.")
        return {'FINISHED'}

    def _bind(self, context, bind_objects, rig, lm_obj) -> bool:
        """Start the Faceit Binding progress on the passed bind objects
        @face_obj: the main object, can also be retrieved from bind_objects (main group)
        @bind_objects: the bind objects. Should have cleared vertex groups except for faceit groups
        @rig: the armature object to bind to
        Returns True if binding was successful, False if not
        """
        faceit_vertex_groups = [
            "faceit_right_eyeball",
            "faceit_left_eyeball",
            "faceit_left_eyes_other",
            "faceit_right_eyes_other",
            "faceit_upper_teeth",
            "faceit_lower_teeth",
            "faceit_tongue",
            "faceit_rigid",
        ]
        # "faceit_eyelashes", "faceit_facial_hair", "faceit_main",
        # ----------------------- SPLIT OBJECTS BEFORE BIND ----------------------------
        # | - Split by Faceit Group assignments
        # | - Sort objects for different bind methods
        # ------------------------------------------------------------------------------
        bind_problem = False
        auto_weight_objects = []
        transfer_weights_objects = []
        eyelashes_objects = []
        secondary_bind_objects = []
        all_split_objects = []
        split_bind_objects_dict = {}

        for obj in bind_objects:
            # Unlock all groups:
            for grp in obj.vertex_groups:
                grp.lock_weight = False
            split_objects = bind_utils.split_by_faceit_groups(obj)
            all_split_objects.extend(split_objects)
            split_bind_objects_dict[obj] = split_objects
        # Remove double entries
        all_split_objects = list(set(all_split_objects))
        futils.clear_object_selection()
        for s_obj in all_split_objects:
            if "faceit_main" in s_obj.vertex_groups:  # or "faceit_tongue" in s_obj.vertex_groups:
                if len(s_obj.vertex_groups) == 1:
                    auto_weight_objects.append(s_obj)
                    continue
            # Remove all vertex groups that don't cover the whole split surface.
            for grp in s_obj.vertex_groups:
                if 'faceit_' in grp.name:
                    vs = vg_utils.get_verts_in_vgroup(s_obj, grp.name)
                    if len(vs) != len(s_obj.data.vertices):
                        # No need to split, the object is already separated
                        print(f'removing {grp.name} from {s_obj.name}')
                        s_obj.vertex_groups.remove(grp)
            if any([grp.name in faceit_vertex_groups for grp in s_obj.vertex_groups]):
                secondary_bind_objects.append(s_obj)
            elif "faceit_facial_hair" in s_obj.vertex_groups or not self.tranfer_to_hair_only:
                transfer_weights_objects.append(s_obj)
                if "faceit_eyelashes" in s_obj.vertex_groups:
                    eyelashes_objects.append(s_obj)
        if self.keep_split_objects:
            print("------- SPLIT OBJECTS ----------")
            print(all_split_objects)
            print("------- Auto Bind ----------")
            print(auto_weight_objects)
            print("------- Data Transfer ----------")
            print(transfer_weights_objects)
            print("------- Secondary Bind ----------")
            print(secondary_bind_objects)
        # --------------- AUTO WEIGHT ---------------------------
        # | - ...
        # -------------------------------------------------------
        start_time = time.time()
        bind_problem, warning = self._auto_weight_objects(
            auto_weight_objects,
            rig,
        )
        if warning:
            self.report(
                {'WARNING'},
                "Automatic Weights failed! {}".format(
                    "Try to activate 'Scale Geometry' in Bind settings."
                    if not self.bind_scale_objects else " Try to use a higher Scale factor."))
        print("Auto Weights in {}".format(round(time.time() - start_time, 2)))
        # ----------------------- SMART WEIGHTS ---------------------------
        # | Remove weights out of the face.
        # -----------------------------------------------------------------
        if self.smart_weights:
            start_time = time.time()
            self._apply_smart_weighting(
                context,
                auto_weight_objects,
                rig,
                lm_obj,
                faceit_vertex_groups,
                smooth_weights=self.smooth_main_edges
            )
            print("Smart Weights in {}".format(round(time.time() - start_time, 2)))

        # brow_bones = ['DEF-brow.B.L', 'DEF-brow.B.L.001', 'DEF-brow.B.L.002', 'DEF-brow.B.L.003',
        #               'DEF-brow.B.R', 'DEF-brow.B.R.001', 'DEF-brow.B.R.002', 'DEF-brow.B.R.003']
        # self._smooth_bone_selection(
        #     auto_weight_objects,
        #     rig,
        #     brow_bones,
        #     factor=.5,
        #     steps=4,
        #     expand=-1.0,
        # )
        # ----------------------- TRANSFER WEIGHTS ---------------------------
        # | Transfer Weights from auto bound geo to secondary geo (hair,...)
        # --------------------------------------------------------------------
        if self.transfer_weights:
            if transfer_weights_objects:
                start_time = time.time()
                self._transfer_weights(
                    auto_weight_objects,
                    transfer_weights_objects,
                )
                if eyelashes_objects:
                    # remove all non lid deform groups from eyelashes
                    lid_bones = [
                        "DEF-lid.B.L",
                        "DEF-lid.B.L.001",
                        "DEF-lid.B.L.002",
                        "DEF-lid.B.L.003",
                        "DEF-lid.T.L",
                        "DEF-lid.T.L.001",
                        "DEF-lid.T.L.002",
                        "DEF-lid.T.L.003",
                        "DEF-lid.B.R",
                        "DEF-lid.B.R.001",
                        "DEF-lid.B.R.002",
                        "DEF-lid.B.R.003",
                        "DEF-lid.T.R",
                        "DEF-lid.T.R.001",
                        "DEF-lid.T.R.002",
                        "DEF-lid.T.R.003",
                    ]
                    if self.clean_eyelashes_weights:
                        for obj in eyelashes_objects:
                            for vgroup in obj.vertex_groups:
                                if "DEF" in vgroup.name:
                                    if vgroup.name not in lid_bones:
                                        obj.vertex_groups.remove(vgroup)
                    # smooth expand eyelashes weights
                    if self.smooth_expand_eyelashes:
                        self.smooth_selected_weights(
                            eyelashes_objects,
                            rig,
                            lid_bones,
                            factor=self.eyelashes_smooth_factor,
                            steps=self.eyelashes_smooth_steps,
                            expand=self.eyelashes_smooth_expand,
                        )
                print("Transfer Weights in {}".format(round(time.time() - start_time, 2)))
        # ----------------------- USER WEIGHTS ---------------------------
        # | Faceit groups -> eyes, teeth, tongue, rigid
        # --------------------------------------------------------------------
        if self.weight_eyes:
            eye_grps = ("faceit_left_eyeball", "faceit_right_eyeball",
                        "faceit_left_eyes_other", "faceit_right_eyes_other")
            for vgroup in eye_grps:
                new_grp = "DEF_eye.L" if "left" in vgroup else "DEF_eye.R"
                self.overwrite_faceit_group(all_split_objects, vgroup, new_grp)

        if self.weight_teeth:
            teeth_grps = ("faceit_upper_teeth", "faceit_lower_teeth")
            for vgroup in teeth_grps:
                if "lower_teeth" in vgroup:
                    if rig.pose.bones.get("DEF-teeth.B"):
                        new_grp = "DEF-teeth.B"
                    else:
                        self.report(
                            {'WARNING'},
                            "Lower Teeth bone 'DEF - teeth.B' does not exist. Create the bone manually or specify Teeth Vertex Groups and regenerate the Rig.")
                        continue
                if "upper_teeth" in vgroup:
                    if rig.pose.bones.get("DEF-teeth.T"):
                        new_grp = "DEF-teeth.T"
                    else:
                        self.report(
                            {'WARNING'},
                            "Uppper Teeth bone 'DEF - teeth.T' does not exist. Create the bone manually or specify Teeth Vertex Groups and regenerate the Rig.")
                        continue
                self.overwrite_faceit_group(all_split_objects, vgroup, new_grp)

        if self.weight_tongue:
            objects_with_vgroup = vg_utils.get_objects_with_vertex_group(
                "faceit_tongue", objects=secondary_bind_objects, get_all=True)
            tongue_bones = [
                "DEF-tongue",
                "DEF-tongue.001",
                "DEF-tongue.002"
            ]
            self._auto_weight_selection_to_bones(objects_with_vgroup, rig, tongue_bones, "faceit_tongue")

        # ----------------------- MERGE SPLIT OBJECTS ---------------------------
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set()
        for obj, split_objects in split_bind_objects_dict.items():
            futils.clear_object_selection()
            for s_obj in split_objects:
                if s_obj:
                    if self.keep_split_objects:
                        debug_duplicate = s_obj.copy()
                        debug_duplicate.data = s_obj.data.copy()
                        context.scene.collection.objects.link(debug_duplicate)
                        debug_duplicate.name = debug_duplicate.name + "_debug"
                    futils.set_active_object(s_obj.name)
            if len(split_objects) > 1:
                futils.set_active_object(obj.name)
                bpy.ops.object.join()
            add_faceit_armature_modifier(obj, rig)

        # ----------------------- SMOOTH ALL ---------------------------
        # | Smooth pass on all bind objects
        # -----------------------------------------------------------------
        if self.smooth_bind:
            self._smooth_weights(
                objects=bind_objects,
                rig=rig,
            )
        # ----------------------- REMOVE RIGID ---------------------------
        # | Remove Weights from Verts with faceit_rigid group (pass only faceit_rigid)
        # -----------------------------------------------------------------
        if self.remove_rigid_weights:
            self.overwrite_faceit_group(bind_objects, "faceit_rigid", new_grp=None)

        for obj in bind_objects:
            for grp in obj.vertex_groups:
                if "faceit_" in grp.name:
                    obj.vertex_groups.remove(grp)

        return not bind_problem

    def _auto_weight_objects(self, auto_weight_objects, rig):
        '''Apply Automatic Weights to main geometry.'''
        auto_weight_problem = False
        return_warning = []
        # Disable bones for auto weighting
        no_auto_weight = [
            "DEF-tongue",
            "DEF-tongue.001",
            "DEF-tongue.002",
            "DEF-teeth.B",
            "DEF-teeth.T",
            "DEF_eye.R",
            "DEF_eye.L",
        ]
        for b in no_auto_weight:
            bone = rig.data.bones.get(b)
            if bone:
                bone.use_deform = False
        warning = "Warning: Bone Heat Weighting: failed to find solution for one or more bones"
        futils.clear_object_selection()
        for obj in auto_weight_objects:
            obj.select_set(state=True)
        futils.set_active_object(rig.name)
        _stdout_warning = ""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            bpy.ops.object.parent_set(type='ARMATURE_AUTO', keep_transform=True)
        stdout.seek(0)
        _stdout_warning = stdout.read()
        del stdout
        if warning in _stdout_warning:
            return_warning.append(
                warning + " for object {}. Check the Docs for work-arounds".format(auto_weight_objects))
            auto_weight_problem = True
        # Reenable Auto weight for bones
        for b in no_auto_weight:
            bone = rig.data.bones.get(b)
            if bone:
                bone.use_deform = True
        return auto_weight_problem, return_warning

    def _apply_smart_weighting(self, context, objects, rig, lm_obj, faceit_vertex_groups, smooth_weights=True):
        '''Remove weights outside of the facial region (landmarks).'''
        # Create the facial hull object encompassing the facial geometry.
        bpy.ops.object.mode_set(mode='OBJECT')
        face_hull = bind_utils.create_facial_hull(context, lm_obj)
        for obj in objects:
            futils.clear_object_selection()
            futils.set_active_object(obj.name)
            deform_groups = vg_utils.get_deform_bones_from_armature(rig)

            if any([grp in obj.vertex_groups for grp in deform_groups]):
                bind_utils.remove_weights_from_non_facial_geometry(obj, face_hull, faceit_vertex_groups)
            else:
                print("found no auto weights on object {}. Skipping smart weights".format(obj.name))
        # remove the hull helper object
        bpy.data.objects.remove(face_hull)
        for obj in objects:
            futils.clear_object_selection()
            rig.select_set(state=True)
            futils.set_active_object(obj.name)
            # Make Def-face the active vertex group before normalizing
            face_grp_idx = obj.vertex_groups.find("DEF-face")
            if face_grp_idx != -1:
                obj.vertex_groups.active_index = face_grp_idx
            use_mask = obj.data.use_paint_mask_vertex
            obj.data.use_paint_mask_vertex = False
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            if smooth_weights:
                # ------------------------- SMOOTH BORDER WEIGHTS -------------------------------
                if face_grp_idx != -1:
                    bpy.ops.object.vertex_group_smooth(group_select_mode='ACTIVE',
                                                       factor=self.main_smooth_factor,
                                                       repeat=self.main_smooth_steps,
                                                       expand=self.main_smooth_expand,
                                                       )
                obj.data.use_paint_mask_vertex = use_mask
            # ------------------------- NORMALIZE WEIGHTS -------------------------------
            # lock and normalize - so the facial influences get restricted
            if face_grp_idx != -1:
                bpy.ops.object.vertex_group_normalize_all(lock_active=True)
            bpy.ops.object.vertex_group_clean(group_select_mode='ALL')
            bpy.ops.object.mode_set()

    def _smooth_weights(self, objects, rig):
        '''Smooth weights on all objects.'''
        for obj in objects:
            futils.clear_object_selection()
            rig.select_set(state=True)
            futils.set_active_object(obj.name)
            use_mask = obj.data.use_paint_mask_vertex
            obj.data.use_paint_mask_vertex = False
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            bpy.ops.object.vertex_group_smooth(group_select_mode='BONE_DEFORM',
                                               factor=self.smooth_factor,
                                               repeat=self.smooth_steps,
                                               expand=self.smooth_expand,
                                               )
            obj.data.use_paint_mask_vertex = use_mask
            bpy.ops.object.mode_set()

    def smooth_selected_weights(
            self, objects, rig, filter_bone_names=None, filter_vertex_group=None, factor=.5, steps=2, expand=1.5):
        '''Smooth weights for a specific selection. Choose from specific bones and/or vertices.'''
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set()
        group_select_mode = 'BONE_DEFORM'
        if filter_bone_names is not None:
            group_select_mode = 'BONE_SELECT'
            futils.clear_object_selection()
            futils.set_active_object(rig.name)
            bpy.ops.object.mode_set(mode='POSE')
            # enable deform bones layer
            bpy.ops.pose.select_all(action='DESELECT')
            any_selected = False
            for bone in filter_bone_names:
                pbone = rig.pose.bones.get(bone)
                if pbone:
                    pbone.bone.select = True
                    any_selected = True
                else:
                    continue
            if not any_selected:
                print("Can't find the specified bones.")
                return
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in objects:
            add_faceit_armature_modifier(obj, rig)
            futils.clear_object_selection()
            futils.set_active_object(rig.name)
            futils.set_active_object(obj.name)

            if filter_vertex_group is not None:
                vs = vg_utils.get_verts_in_vgroup(obj, filter_vertex_group)
                if not vs:
                    continue
                # select all verts in grp
                mesh_utils.select_vertices(obj, vs, deselect_others=True)
                obj.data.use_paint_mask_vertex = True
                use_mask = obj.data.use_paint_mask_vertex

            # smooth weights
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            bpy.ops.object.vertex_group_smooth(
                group_select_mode=group_select_mode,
                factor=factor,
                repeat=steps,
                expand=expand
            )
            if filter_vertex_group is not None:
                obj.data.use_paint_mask_vertex = use_mask
            bpy.ops.object.mode_set(mode='OBJECT')

    def _transfer_weights(self, transfer_from_objects, transfer_to_objects):
        if transfer_to_objects and transfer_from_objects:
            for from_obj in transfer_from_objects:
                futils.clear_object_selection()
                for obj in transfer_to_objects:
                    faceit_groups_per_obj = set(vg_utils.get_faceit_vertex_grps(obj))
                    # get objects that were not bound and are registered in faceit objects
                    bind_utils.data_transfer_vertex_groups(obj_from=from_obj, obj_to=obj, method='NEAREST')
                    # remove all faceit groups that were transferred from the auto bind objects. These will messup re-binding.
                    for grp in set(vg_utils.get_faceit_vertex_grps(obj)) - faceit_groups_per_obj:
                        false_assigned_faceit_group = obj.vertex_groups.get(grp)
                        obj.vertex_groups.remove(false_assigned_faceit_group)
        bpy.ops.object.mode_set()

    def _auto_weight_selection_to_bones(
            self, auto_weight_objects, rig, bones, faceit_group="faceit_tongue"):
        '''Bind a vertex selection to specific bones'''
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set()
        futils.clear_object_selection()
        futils.set_active_object(rig.name)
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        any_selected = False
        for bone in bones:
            pbone = rig.pose.bones.get(bone)
            if pbone:
                pbone.bone.select = True
                any_selected = True
            else:
                continue
        if not any_selected:
            self.report({'WARNING'}, f"{faceit_group} bones do not exist. Regenerate the rig.")
            return
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in auto_weight_objects:
            futils.clear_object_selection()
            futils.set_active_object(rig.name)
            futils.set_active_object(obj.name)

            vs = vg_utils.get_verts_in_vgroup(obj, faceit_group)
            if not vs:
                continue
            # Add Faceit_Armature mod
            add_faceit_armature_modifier(obj, rig)
            # remove all weights of other bones that got weighted in autoweighting process
            vg_utils.remove_vgroups_from_verts(obj, vs=vs, filter_keep=faceit_group)
            if vg_utils.vertex_group_sanity_check(obj):
                vg_utils.remove_zero_weights_from_verts(obj)
                vg_utils.remove_unused_vertex_groups_thresh(obj)

            # select all verts in tongue grp
            mesh_utils.select_vertices(obj, vs, deselect_others=True)

            # go weightpaint
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            use_mask = obj.data.use_paint_mask_vertex
            obj.data.use_paint_mask_vertex = True
            bpy.ops.paint.weight_from_bones(type='AUTOMATIC')
            # smooth deform
            bpy.ops.object.vertex_group_smooth(
                group_select_mode='BONE_SELECT', factor=.5, repeat=2, expand=1.5)
            # reset settings
            obj.data.use_paint_mask_vertex = use_mask
            bpy.ops.object.mode_set(mode='OBJECT')

    def overwrite_faceit_group(self, objects, faceit_vertex_group, new_grp=""):
        """
        bind user defined vertices to respective bones with constant weight of 1 on all vertices
        @objects - the bind objects
        @faceit_vertex_group - the user defined groups holding all vertices that should be assigned to new group
        @new_grp - the name of the new vertex group
        """
        # get all vertices in the faceit group
        objects_with_vgroup = vg_utils.get_objects_with_vertex_group(
            faceit_vertex_group, objects=objects, get_all=True)
        for obj in objects_with_vgroup:
            vs = vg_utils.get_verts_in_vgroup(obj, faceit_vertex_group)
            if not vs:
                continue
            vg_utils.remove_all_weight(obj, vs)
            if new_grp:
                vg_utils.assign_vertex_grp(obj, [v.index for v in vs], new_grp)


class FACEIT_OT_PairArmature(bpy.types.Operator):
    '''Pair the FaceitRig to the facial objects without generating weights'''
    bl_idname = "faceit.pair_armature"
    bl_label = "Pair Armature"
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        faceit_objects = futils.get_faceit_objects_list()
        faceit_rig = futils.get_faceit_armature(force_original=True)
        if not faceit_rig:
            return {'CANCELLED'}

        for obj in faceit_objects:
            add_faceit_armature_modifier(obj, faceit_rig)

        context.scene.faceit_weights_restorable = False

        return {'FINISHED'}


class FACEIT_OT_UnbindFacial(bpy.types.Operator):
    '''Unbind the FaceitRig from the facial objects'''
    bl_idname = "faceit.unbind_facial"
    bl_label = "Unbind"
    bl_options = {'UNDO', 'INTERNAL'}

    remove_deform_groups: bpy.props.BoolProperty(
        name="Remove Binding Groups",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        rig = futils.get_faceit_armature()
        faceit_objects = futils.get_faceit_objects_list()
        for obj in faceit_objects:
            a_mod = get_faceit_armature_modifier(obj)
            if a_mod:
                obj.modifiers.remove(a_mod)
            if self.remove_deform_groups:
                if rig:
                    vg_utils.remove_deform_vertex_grps(
                        obj, armature=rig)
        return {'FINISHED'}


class FACEIT_OT_CorrectiveSmooth(bpy.types.Operator):
    '''Add corrective smooth modifier to the active object'''

    bl_idname = "faceit.smooth_correct"
    bl_label = "Smooth Correct Modifier"
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is not None:
            if context.mode == 'OBJECT' and obj.type == 'MESH':
                if not obj.modifiers.get("Faceit_CorrectiveSmooth"):
                    return True

    def execute(self, context):
        obj = context.object
        mod = obj.modifiers.new(name="Faceit_CorrectiveSmooth", type="CORRECTIVE_SMOOTH")
        mod.smooth_type = "LENGTH_WEIGHTED"
        mod.iterations = 4
        mod.use_pin_boundary = True
        arm_mod = get_faceit_armature_modifier(obj)
        if arm_mod and mod:
            index = obj.modifiers.find(arm_mod.name) + 1
            override = {'object': obj, 'active_object': obj}
            bpy.ops.object.modifier_move_to_index(
                override,
                modifier=mod.name,
                index=index
            )
        set_bake_modifier_item(mod, set_bake=True, is_faceit_mod=True)
        return {'FINISHED'}
