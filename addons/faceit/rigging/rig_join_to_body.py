
import bpy
from bpy.props import BoolProperty
from mathutils import Vector

from ..core.modifier_utils import get_faceit_armature_modifier, populate_bake_modifier_items, set_mod_bake
from ..panels.draw_utils import draw_text_block

from ..animate.animate_utils import restore_constraints_to_default_values
from ..bind.bind_utils import data_transfer_vertex_groups
from ..core import faceit_utils as futils
from ..core.vgroup_utils import (assign_vertex_grp,
                                 get_deform_bones_from_armature,
                                 invert_vertex_group_weights)
from ..ctrl_rig.control_rig_data import get_random_rig_id
from .rig_utils import get_bone_groups_dict, set_bone_groups_from_dict


class FACEIT_OT_JoinWithBodyArmature(bpy.types.Operator):
    '''Remove the def face group to use the faceit armature in regular keyframe animation'''
    bl_idname = 'faceit.join_with_body_armature'
    bl_label = 'Join to Body'
    bl_options = {'UNDO', 'INTERNAL'}

    combine_animation: BoolProperty(
        name='Combine Actions',
        default=False,
        description=''
    )
    is_arp_body: BoolProperty(
        name='Auto Rig Pro',
        default=False,
        options={'SKIP_SAVE', },
    )
    tag_arp_custom: BoolProperty(
        name='Tag Custom',
        default=False,
        options={'SKIP_SAVE', },
        description='Tag the deform bones with a custom property so they will be exported in ARP operators.'
    )
    merge_faceit_weights: BoolProperty(
        name='Merge Faceit Weights',
        default=True,
        description='Overwrite any weights below Face weights, keeping Faceit weights in tact. If this is disabled, the Faceit weights will be removed.',

    )
    keep_faceit_bone_groups: BoolProperty(
        name='Keep Bone Groups',
        default=True,
        description='Keep Bone Groups and Colors from the Faceit rig',
    )
    use_armature_modifier_for_baking: BoolProperty(
        name='Use Armature Modifier for Baking',
        description='Use armature modifier for baking the shape keys.',
        default=True,
    )

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            if context.scene.faceit_armature:
                if context.scene.faceit_body_armature and context.scene.faceit_body_armature_head_bone:
                    return True

    def invoke(self, context, event):
        scene = context.scene
        body_rig = scene.faceit_body_armature
        faceit_rig = futils.get_faceit_armature(force_original=True)
        if body_rig.scale != faceit_rig.scale:
            if body_rig.scale != Vector((1,) * 3):
                self.report(
                    {'ERROR'},
                    f"Body and Faceit rigs have different scales. Please apply the scale on the Body Armature '{body_rig.name}' first.")
                return {'CANCELLED'}
            if Vector((round(i, 3) for i in faceit_rig.scale)) != Vector((1,) * 3):
                self.report(
                    {'ERROR'},
                    f"Body and Faceit rigs have different scales. Please apply the scale on the Faceit Armature '{faceit_rig.name}' first.")
                return {'CANCELLED'}
        self.tag_arp_custom = self.is_arp_body = any(x.startswith('arp_') for x in scene.faceit_body_armature.keys())

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        draw_text_block(
            layout=layout,
            text='This operation is destructive. You can\'t go back to landmarks anymore.',
            heading='DESTRUCTIVE'
        )
        row = layout.row()
        row.prop(self, 'merge_faceit_weights', icon='MOD_VERTEX_WEIGHT')
        if self.merge_faceit_weights:
            draw_text_block(
                layout=layout,
                text='Body Weights will be overwritten in Face area.',
                heading='WARNING'
            )
        row = layout.row()
        row.prop(self, 'keep_faceit_bone_groups', icon='GROUP_BONE')
        if self.is_arp_body:
            row = layout.row()
            row.label(text='Auto Rig Pro detected:')
            if 'c_eye_target.x' in context.scene.faceit_body_armature.pose.bones:
                draw_text_block(
                    layout=layout,
                    text='ARP Face Rig detected. Consider Removing it.',
                    heading='WARNING'
                )
            row = layout.row()
            row.prop(self, 'tag_arp_custom', icon='EVENT_C')
            if self.tag_arp_custom:
                draw_text_block(
                    layout=layout,
                    text='ARP export to game engines might not work as expected.',
                    heading='WARNING'
                )
        row = layout.row()
        row.prop(self, 'use_armature_modifier_for_baking', icon='MOD_ARMATURE')

    def execute(self, context):

        scene = context.scene
        warning = False
        # --------------- SCENE SETTINGS -----------------------
        # - Get all relevant settings and objects
        # ------------------------------------------------------
        body_rig = scene.faceit_body_armature
        faceit_rig = futils.get_faceit_armature(force_original=True)
        if not faceit_rig:
            self.report({'ERROR'}, 'The Faceit Armature doesn\'t exist')
            return {'CANCELLED'}
        head_bone_name = scene.faceit_body_armature_head_bone
        head_bone = body_rig.data.bones.get(head_bone_name)
        if not head_bone:
            self.report({'ERROR'}, f'The selected bone {head_bone_name} does not exist.')
            return {'CANCELLED'}
        faceit_objects = futils.get_faceit_objects_list()
        if not any((futils.is_collection_visible(context, coll) for coll in body_rig.users_collection)):
            self.report({'ERROR'}, f'The Body Rig {body_rig.name} is not visible in any collection.')
            return {'CANCELLED'}
        futils.get_faceit_collection()
        futils.set_hide_obj(body_rig, False)
        futils.set_hide_obj(faceit_rig, False)

        auto_normalize = scene.tool_settings.use_auto_normalize
        scene.tool_settings.use_auto_normalize = False

        # Combined Rig layer status
        rig_layers_combined = [a or b for a, b in zip(faceit_rig.data.layers, body_rig.data.layers)]
        # The Bone Groups from Faceit Rig
        if self.keep_faceit_bone_groups:
            faceit_bone_groups = get_bone_groups_dict(faceit_rig)
        # Force Rest Position
        faceit_rig.data.pose_position = 'REST'
        body_rig.data.pose_position = 'REST'
        if self.tag_arp_custom:
            # Get all bone names for ARP custom tags
            all_faceit_bones = [b.name for b in faceit_rig.pose.bones]
        # Find child objects of relevant body rig bones
        head_bone_children = head_bone.children_recursive
        bone_children_dict_body = {}
        for obj in faceit_objects:
            for b in head_bone_children:
                if b.name == obj.parent_bone:
                    try:
                        bone_children_dict_body[b].append(obj)
                    except (KeyError, AttributeError):
                        bone_children_dict_body[b] = [obj, ]
                    if obj.children:
                        for obj_child in obj.children_recursive:
                            bone_children_dict_body[b].append(obj_child)
                    break
        # Change the relation from parent to weighted
        for bone, child_objects in bone_children_dict_body.items():
            for body_child in child_objects:
                mod_exists = False
                for mod in body_child.modifiers:
                    if mod.type == 'ARMATURE':
                        if mod.object:
                            if mod.object.name == body_rig.name:
                                mod_exists = True
                if not mod_exists:
                    mod = body_child.modifiers.new(name="Armature", type='ARMATURE')
                    mod.object = body_rig
                body_child.parent_type = 'OBJECT'
                if body_child.vertex_groups.find(bone.name) == -1:
                    body_child.vertex_groups.new(name=bone.name)
                # Assign vertices to group
                assign_vertex_grp(
                    body_child, vertices=[v.index for v in body_child.data.vertices],
                    grp_name=bone.name)
        # Get faceit deform vertex groups names
        all_faceit_deform_groups = get_deform_bones_from_armature(faceit_rig)
        body_deform_groups = get_deform_bones_from_armature(body_rig)
        if any(x in body_deform_groups for x in all_faceit_deform_groups):
            self.report(
                {'WARNING'},
                'Some vertex groups are used in both armatures! The combined result may not be as expected.')
            warning = True

        # --------------- MERGE WEIGHTS ------------------------
        # - Split individual surfaces of all bound objects
        # - Get all face weights in a single group (inverse of def-face)
        # - Normalize body weights, lock the new group
        # - transfer the new body weights back to the original
        # - Join the original objects
        # ------------------------------------------------------
        if self.merge_faceit_weights:
            def find_vgroups(obj, vgroups_to_find):
                ''' Returns True if any of the @vgroups (list[String]) is found in @obj vertex groups'''
                return any(vg.name in vgroups_to_find for vg in obj.vertex_groups)
            # Remove Rigid group
            face_deform_groups = all_faceit_deform_groups.copy()
            face_deform_groups.remove('DEF-face')
            # Get all face objects that are bound to the faceit armature
            objects_to_process = [obj for obj in faceit_objects if find_vgroups(
                obj, all_faceit_deform_groups)]  # and find_vgroups(obj, body_deform_groups)]
            if not objects_to_process:
                self.report(
                    {'ERROR'},
                    f'Both rigs need to be bound to the registered objects! Please bind the {faceit_rig} to the objects first')
                return {'CANCELLED'}
            for obj in objects_to_process:
                print(f'Start process on {obj.name}')
                futils.set_hidden_state_object(obj, False, False)
                # Store vertex lock states
                vg_lock_state_dict = {vg.name: vg.lock_weight for vg in obj.vertex_groups}
                # Hide all modifiers
                mod_show_dict = {}
                for mod in obj.modifiers:
                    mod_show_dict[mod.name] = mod.show_viewport
                    mod.show_viewport = False
                dup_ob = futils.duplicate_obj(obj, link=True)
                def_face_grp_dup = dup_ob.vertex_groups.get('DEF-face')
                # Get the body weights to be normalized
                relevant_groups = body_deform_groups
                if def_face_grp_dup:
                    relevant_groups.append(def_face_grp_dup.name)

                # Remove all vertex groups that are not relevant
                for grp in dup_ob.vertex_groups:
                    if grp.name not in relevant_groups:
                        dup_ob.vertex_groups.remove(grp)
                    else:
                        grp.lock_weight = False

                # Create the inverse group; if def-face does not exist, assign all verts to inverse
                if def_face_grp_dup:
                    def_face_inv = invert_vertex_group_weights(dup_ob, def_face_grp_dup)
                else:
                    vs = [v.index for v in dup_ob.data.vertices]
                    assign_vertex_grp(dup_ob, vs, 'DEF-face_invert')

                def_face_inv = dup_ob.vertex_groups.get('DEF-face_invert')

                if def_face_grp_dup:
                    dup_ob.vertex_groups.remove(def_face_grp_dup)

                if len(dup_ob.vertex_groups) > 1:

                    # Normalize all weights, lock the face area
                    def_face_inv.lock_weight = True
                    futils.clear_object_selection()
                    futils.set_active_object(dup_ob.name)
                    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
                    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
                    bpy.ops.object.mode_set()

                dup_ob.vertex_groups.remove(def_face_inv)

                # Transfer the weights to the original, lock the face weights
                for vg in obj.vertex_groups:
                    if vg.name in face_deform_groups:
                        vg.lock_weight = True
                data_transfer_vertex_groups(dup_ob, obj)
                # Remove the duplicate obj
                bpy.data.objects.remove(dup_ob)
                # --------------- OBJECT SETTINGS -------------------
                # | - Remove Faceit Armature Mod
                # | - Restore Modifier Visibility States
                # | - Ensure Body Armature Mod
                # -------------------------------------------------------
                # Restore lock state
                for vg_name, lock in vg_lock_state_dict.items():
                    vg = obj.vertex_groups.get(vg_name)
                    if vg:
                        vg.lock_weight = lock
                def_face_grp = obj.vertex_groups.get('DEF-face')
                if def_face_grp:
                    obj.vertex_groups.remove(def_face_grp)
                found_body_armature_mod = False
                # Restore the hide states of all other modifiers
                for mod, show_value in mod_show_dict.items():
                    mod = obj.modifiers.get(mod)
                    if mod:
                        mod.show_viewport = show_value
                        if mod.type == 'ARMATURE' and mod.object == body_rig:
                            found_body_armature_mod = True
                            mod.show_viewport = True
                # Ensure Body Armature mod
                if not found_body_armature_mod:
                    mod = obj.modifiers.new(name='Armature', type='ARMATURE')
                    mod.object = body_rig
        # Finally, remove armature modifier, if not merge weights -> remove faceit weights
        for obj in futils.get_faceit_objects_list():
            # Don't merge Faceit Weights --> Remove them
            if not self.merge_faceit_weights:
                for vg in obj.vertex_groups:
                    if vg.name in all_faceit_deform_groups:
                        obj.vertex_groups.remove(vg)
            # Remove the Faceit armature modifier
            arm_mod = get_faceit_armature_modifier(obj)
            if arm_mod:
                obj.modifiers.remove(arm_mod)
        # --------------- JOIN THE ARMATURES -------------------
        # - Store the Faceit bone groups
        # - Join Faceit bones into body armature
        # - Set the face parent bone
        # - Apply the Faceit bone groups to body armature
        # - Restore layers of both armatures
        # ------------------------------------------------------
        # Join the armatures
        futils.clear_object_selection()
        futils.set_active_object(faceit_rig.name)
        futils.set_active_object(body_rig)
        bpy.ops.object.join()
        futils.clear_object_selection()
        futils.set_active_object(body_rig.name)
        bpy.ops.object.mode_set(mode='EDIT')
        face_bone = body_rig.data.edit_bones.get('DEF-face')
        head_bone_edit = body_rig.data.edit_bones.get(head_bone_name)
        # Restore rigify naming and layers for face bone
        face_bone.name = 'ORG-face'
        face_bone.use_deform = False
        face_bone.layers[31] = True
        face_bone.layers[29] = False
        face_bone.parent = head_bone_edit
        if self.keep_faceit_bone_groups:
            bpy.ops.object.mode_set(mode='POSE')
            set_bone_groups_from_dict(body_rig, bone_groups_dict=faceit_bone_groups)
        # Remove copy rotation eye bone constraints:
        eyelid_def_bones = [
            'DEF-lid.B.L',
            'DEF-lid.B.L.001',
            'DEF-lid.B.L.002',
            'DEF-lid.B.L.003',
            'DEF-lid.T.L',
            'DEF-lid.T.L.001',
            'DEF-lid.T.L.002',
            'DEF-lid.T.L.003',
            'DEF-lid.B.R',
            'DEF-lid.B.R.001',
            'DEF-lid.B.R.002',
            'DEF-lid.B.R.003',
            'DEF-lid.T.R',
            'DEF-lid.T.R.001',
            'DEF-lid.T.R.002',
            'DEF-lid.T.R.003',
        ]
        for b in eyelid_def_bones:
            bone = body_rig.pose.bones.get(b)
            for c in bone.constraints:
                if c.type == 'COPY_ROTATION':
                    bone.constraints.remove(c)
        bpy.ops.object.mode_set()
        body_rig.data.layers = rig_layers_combined[:]
        if self.tag_arp_custom:
            all_faceit_bones.append('ORG-face')
            for b in body_rig.pose.bones:
                if b.name in all_faceit_bones:
                    b['cc'] = 1.0
        populate_bake_modifier_items(faceit_objects)
        if self.use_armature_modifier_for_baking:
            for obj in faceit_objects:
                for mod in obj.modifiers:
                    if mod.type == 'ARMATURE':
                        if mod.object == body_rig:
                            set_mod_bake(obj, mod, True)
        # Restore POSE position
        body_rig.data.pose_position = 'POSE'

        # --------------- SCENE SETTINGS -------------------
        # - Set Faceit Armature if user choosed
        # ------------------------------------------------------
        if not body_rig.get('faceit_rig_id'):
            body_rig['faceit_rig_id'] = get_random_rig_id()

        scene.faceit_armature = body_rig
        if not scene.faceit_shapes_generated:
            faceit_action = bpy.data.actions.get('overwrite_shape_action')
            if getattr(body_rig, 'animation_data') and faceit_action:
                # if getattr(body_rig.animation_data, 'action')
                body_rig.animation_data.action = faceit_action
        else:
            if body_rig.animation_data:
                body_rig.animation_data.action = None
        #     scene.faceit_armature = None

        scene.tool_settings.use_auto_normalize = auto_normalize
        if not warning:
            self.report({'INFO'}, f'Succesfully joined the FaceitRig to the armature {body_rig.name}')
        scene.faceit_workspace.active_tab = 'BAKE'
        return {'FINISHED'}
