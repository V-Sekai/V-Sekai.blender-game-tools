
import bmesh
import bpy
from bpy.props import BoolProperty
from bpy.types import ParticleSystem
from mathutils import Vector
import timeit
from ..core.mesh_utils import GeometryIslands

from ..core.modifier_utils import get_faceit_armature_modifier, populate_bake_modifier_items, set_mod_bake
from ..panels.draw_utils import draw_text_block

from ..core import faceit_utils as futils
from ..core.vgroup_utils import (
    apply_vertex_group,
    assign_vertex_grp,
    cleanup_vertex_groups,
    get_deform_bones_from_armature,
    invert_vertex_group_weights,
    store_vertex_group
)
from ..ctrl_rig.control_rig_data import get_random_rig_id
from .rig_utils import get_bone_groups_dict, reset_stretch, set_bone_groups_from_dict


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
        default=False,
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
        if bpy.app.version < (4, 0, 0):
            self.keep_faceit_bone_groups = True

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        draw_text_block(
            context,
            layout=layout,
            text='This operation is destructive. You can\'t go back to landmarks anymore.',
            heading='DESTRUCTIVE',
            in_operator=True,
        )
        row = layout.row()
        row.prop(self, 'merge_faceit_weights', icon='MOD_VERTEX_WEIGHT')
        if self.merge_faceit_weights:
            draw_text_block(
                context,
                layout=layout,
                text='Body Weights will be overwritten in Face area.',
                heading='WARNING',
                in_operator=True,
            )
        if bpy.app.version < (4, 0, 0):
            row = layout.row()
            row.prop(self, 'keep_faceit_bone_groups', icon='GROUP_BONE')
        if self.is_arp_body:
            row = layout.row()
            row.label(text='Auto Rig Pro detected:')
            if 'c_eye_target.x' in context.scene.faceit_body_armature.pose.bones:
                draw_text_block(
                    context,
                    layout=layout,
                    text='ARP Face Rig detected. Consider Removing it.',
                    heading='WARNING',
                    in_operator=True
                )
            row = layout.row()
            row.prop(self, 'tag_arp_custom', icon='EVENT_C')
            if self.tag_arp_custom:
                draw_text_block(
                    context,
                    layout=layout,
                    text='ARP export to game engines might not work as expected.',
                    heading='WARNING',
                    in_operator=True
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
        rig_type = futils.get_rig_type(faceit_rig)

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
        if bpy.app.version < (4, 0, 0):
            rig_layers_combined = [a or b for a, b in zip(faceit_rig.data.layers, body_rig.data.layers)]
            # The Bone Groups from Faceit Rig
            if self.keep_faceit_bone_groups:
                faceit_bone_groups = get_bone_groups_dict(faceit_rig)
        else:
            rig_layers_combined = {}
            for c in faceit_rig.data.collections:
                rig_layers_combined[c.name] = c.is_visible
            for c in body_rig.data.collections:
                if c.name in rig_layers_combined:
                    rig_layers_combined[c.name] |= c.is_visible
                else:
                    rig_layers_combined[c.name] = c.is_visible
        # Force Rest Position
        faceit_rig.data.pose_position = 'REST'
        body_rig.data.pose_position = 'REST'
        if self.tag_arp_custom:
            # Get all bone names for ARP custom tags
            all_faceit_bones = [b.name for b in faceit_rig.pose.bones]
        # Find child objects of relevant body rig bones
        head_bone_children = head_bone.children_recursive
        head_bone_children.append(head_bone)
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
        all_faceit_deform_groups = set(get_deform_bones_from_armature(faceit_rig))
        body_deform_groups = get_deform_bones_from_armature(body_rig)
        if any(x in body_deform_groups for x in all_faceit_deform_groups):
            self.report(
                {'WARNING'},
                'Some vertex groups are used in both armatures! The combined result may not be as expected.')
            warning = True
        # --------------- MERGE WEIGHTS ------------------------
        # - Get all face weights in a single group (inverse of def-face)
        # - Normalize body weights, lock the new group
        # - Existing face weights and unrelated groups are preserved.
        # ------------------------------------------------------
        if self.merge_faceit_weights:
            def find_vgroups(obj, vgroups_to_find):
                ''' Returns True if any of the @vgroups (list[String]) is found in @obj vertex groups'''
                return any(vg.name in vgroups_to_find for vg in obj.vertex_groups)
            # Get all face objects that are bound to the faceit armature
            objects_to_process = [obj for obj in faceit_objects if find_vgroups(
                obj, all_faceit_deform_groups)]  # and find_vgroups(obj, body_deform_groups)]
            if not objects_to_process:
                self.report(
                    {'ERROR'},
                    f'Both rigs need to be bound to the registered objects! Please bind the {faceit_rig} to the objects first')
                return {'CANCELLED'}
            # Remove all vertex groups that are not relevant
            normalize_groups = set(body_deform_groups)
            normalize_groups.add('DEF-face_invert')
            for obj in objects_to_process:
                def_face_grp = obj.vertex_groups.get('DEF-face')
                found_faceit_groups = all_faceit_deform_groups.intersection(obj.vertex_groups.keys())
                if not def_face_grp and not found_faceit_groups:
                    print(f'No Faceit groups found on {obj.name}')
                    continue
                found_relevant_groups = normalize_groups.intersection(obj.vertex_groups.keys())
                if not found_relevant_groups:
                    print(f'No body groups found on {obj.name}')
                    continue
                time_total = timeit.default_timer()
                print(f'Start process on {obj.name}')
                # Get the indices of the existing faceit groups
                faceit_group_indices = set(vg.index for vg in obj.vertex_groups if vg.name in found_faceit_groups)
                futils.set_hidden_state_object(obj, False, False)
                # Store vertex lock states
                vg_lock_state_dict = {vg.name: vg.lock_weight for vg in obj.vertex_groups}
                # Store particle system vertex groups
                particle_system_groups = {}
                for p in obj.particle_systems:
                    groups_dict = particle_system_groups[p.name] = {}
                    groups_dict['vertex_group_clump'] = p.vertex_group_clump
                    groups_dict['vertex_group_density'] = p.vertex_group_density
                    groups_dict['vertex_group_field'] = p.vertex_group_field
                    groups_dict['vertex_group_kink'] = p.vertex_group_kink
                    groups_dict['vertex_group_length'] = p.vertex_group_length
                    groups_dict['vertex_group_rotation'] = p.vertex_group_rotation
                    groups_dict['vertex_group_roughness_1'] = p.vertex_group_roughness_1
                    groups_dict['vertex_group_roughness_2'] = p.vertex_group_roughness_2
                    groups_dict['vertex_group_roughness_end'] = p.vertex_group_roughness_end
                    groups_dict['vertex_group_size'] = p.vertex_group_size
                    groups_dict['vertex_group_tangent'] = p.vertex_group_tangent
                    groups_dict['vertex_group_twist'] = p.vertex_group_twist
                    groups_dict['vertex_group_velocity'] = p.vertex_group_velocity
                time = timeit.default_timer()
                # Get vertex ids for all islands that have faceit groups assigned.
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                geo_islands = GeometryIslands(bm.verts)
                relevant_vert_ids = set()  # Vertices that should not be affected by the normalization
                for island in geo_islands.islands:
                    vert_indices = [v.index for v in island]
                    # check if the island has faceit groups
                    for i in vert_indices:
                        v = obj.data.vertices[i]
                        if not v.groups:
                            continue
                        if any(g.group in faceit_group_indices for g in v.groups):
                            relevant_vert_ids.update(vert_indices)
                            break
                # Skip islands that have no faceit groups.
                if not relevant_vert_ids:
                    print(f'No relevant vertices found on {obj.name}')
                    # The Faceit groups are empty. Remove them:
                    for vg_name in found_faceit_groups:
                        vg = obj.vertex_groups.get(vg_name)
                        if vg:
                            obj.vertex_groups.remove(vg)
                    continue
                time = timeit.default_timer() - time
                print(f'Finished get relevant vertices on {obj.name} in {time:.2f} seconds')
                # Invert the faceit group
                time = timeit.default_timer()
                if def_face_grp:
                    vs = [v for v in obj.data.vertices if v.index in relevant_vert_ids]
                    invert_vertex_group_weights(obj, def_face_grp, vs=vs)
                    obj.vertex_groups.remove(def_face_grp)
                elif any(x in obj.vertex_groups for x in all_faceit_deform_groups):
                    assign_vertex_grp(obj, list(relevant_vert_ids), 'DEF-face_invert')
                else:
                    continue
                # Store the faceit weights and all other groups that should not be normalized.
                stored_other_groups = {}
                for grp in obj.vertex_groups:
                    if grp.name in normalize_groups and grp.name not in found_faceit_groups:
                        grp.lock_weight = False
                    else:
                        # Store and Remove other groups before normalizing.
                        vertex_data = store_vertex_group(obj, grp)
                        if vertex_data:
                            stored_other_groups[grp.name] = vertex_data
                        obj.vertex_groups.remove(grp)
                time = timeit.default_timer() - time
                print(f'Finished remove irrelevant groups on {obj.name} in {time:.2f} seconds')
                if bpy.app.version > (3, 6, 0):
                    # add a bone to the body armature 'DEF-face_invert' as deform bone
                    # vertex group normalize seems to be broken in 3.6
                    futils.clear_object_selection()
                    futils.set_active_object(body_rig)
                    bpy.ops.object.mode_set(mode='EDIT')
                    edit_bones = body_rig.data.edit_bones
                    new_bone = edit_bones.new("DEF-face_invert")
                    new_bone.use_deform = True
                    new_bone.head = (0, 0, 0)
                    new_bone.tail = (0, 0, 1)
                    bpy.ops.object.mode_set(mode='OBJECT')

                def_face_inv_grp = obj.vertex_groups.get('DEF-face_invert')
                def_face_inv_grp.lock_weight = True

                if bpy.app.version < (3, 6, 0):
                    override = {'object': obj, 'active_object': obj, }
                    bpy.ops.object.vertex_group_normalize_all(override, group_select_mode='ALL', lock_active=False)
                else:
                    with bpy.context.temp_override(object=obj, active_object=obj):
                        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
                if bpy.app.version > (3, 6, 0):
                    # remove the helper bone
                    futils.clear_object_selection()
                    futils.set_active_object(body_rig)
                    bpy.ops.object.mode_set(mode='EDIT')
                    edit_bones = body_rig.data.edit_bones
                    edit_bones.remove(edit_bones.get("DEF-face_invert"))
                    bpy.ops.object.mode_set(mode='OBJECT')
                # Restore the faceit weights / other vertex groups
                for vg_name, data in stored_other_groups.items():
                    if vg_name in obj.vertex_groups:
                        obj.vertex_groups.remove(obj.vertex_groups[vg_name])
                    vg = obj.vertex_groups.new(name=vg_name)
                    apply_vertex_group(vg, data)
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
                obj.vertex_groups.remove(def_face_inv_grp)
                cleanup_vertex_groups(obj, context=context, limit=0.00001)

                for p_name, groups_dict in particle_system_groups.items():
                    p: ParticleSystem = obj.particle_systems[p_name]
                    p.vertex_group_clump = groups_dict['vertex_group_clump']
                    p.vertex_group_density = groups_dict['vertex_group_density']
                    p.vertex_group_field = groups_dict['vertex_group_field']
                    p.vertex_group_kink = groups_dict['vertex_group_kink']
                    p.vertex_group_length = groups_dict['vertex_group_length']
                    p.vertex_group_rotation = groups_dict['vertex_group_rotation']
                    p.vertex_group_roughness_1 = groups_dict['vertex_group_roughness_1']
                    p.vertex_group_roughness_2 = groups_dict['vertex_group_roughness_2']
                    p.vertex_group_roughness_end = groups_dict['vertex_group_roughness_end']
                    p.vertex_group_size = groups_dict['vertex_group_size']
                    p.vertex_group_tangent = groups_dict['vertex_group_tangent']
                    p.vertex_group_twist = groups_dict['vertex_group_twist']
                    p.vertex_group_velocity = groups_dict['vertex_group_velocity']
                time = timeit.default_timer() - time_total
                print(f'Finished process on {obj.name} in {time:.2f} seconds')
            for obj in objects_to_process:
                found_body_armature_mod = False
                # Restore the hide states of all other modifiers
                for mod in obj.modifiers:
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
        # return {'FINISHED'}
        futils.clear_object_selection()
        futils.set_active_object(faceit_rig.name)
        futils.set_active_object(body_rig)
        body_rig.data.show_bone_custom_shapes = True
        shapes_generated = scene.faceit_shapes_generated
        bpy.ops.object.join()
        reset_stretch(rig_obj=body_rig)
        scene.faceit_shapes_generated = shapes_generated
        futils.clear_object_selection()
        futils.set_active_object(body_rig.name)
        bpy.ops.object.mode_set(mode='EDIT')
        head_bone_edit = body_rig.data.edit_bones.get(head_bone_name)
        if rig_type != 'RIGIFY_NEW':
            face_bone = body_rig.data.edit_bones.get('DEF-face')
            # Restore rigify naming and layers for face bone
            face_bone.name = 'ORG-face'
            face_bone.use_deform = False
        else:
            face_bone = body_rig.data.edit_bones.get('ORG-face')
        face_bone.parent = head_bone_edit
        if bpy.app.version < (4, 0, 0):
            face_bone.layers[31] = True
            face_bone.layers[29] = False
            if self.keep_faceit_bone_groups:
                bpy.ops.object.mode_set(mode='POSE')
                set_bone_groups_from_dict(body_rig, bone_groups_dict=faceit_bone_groups)
        else:
            l31 = body_rig.data.collections.get('Layer 31')
            if l31:
                l31.assign(face_bone)
            l29 = body_rig.data.collections.get('Layer 29')
            if l29:
                l29.assign(face_bone)
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
        if bpy.app.version < (4, 0, 0):
            body_rig.data.layers = rig_layers_combined[:]
        else:
            for c in body_rig.data.collections:
                c.is_visible = rig_layers_combined[c.name]
            # For some reason the eye follow constraint is not updated properly in 4.0
            mch_bone = body_rig.pose.bones.get('MCH-eyes_parent')
            if mch_bone:
                c = mch_bone.constraints[0]
                c.influence = 0.5
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
