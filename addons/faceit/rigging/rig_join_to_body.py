
import bpy
from bpy.props import BoolProperty

from .rig_utils import get_bone_groups_dict, set_bone_groups_from_dict

from ..core import faceit_utils as futils
from ..ctrl_rig.control_rig_data import get_random_rig_id
from ..bind.bind_utils import split_object, _data_transfer_vertex_groups
from ..animate.animate_utils import restore_constraints_to_default_values
from ..core.vgroup_utils import get_deform_bones_from_armature, invert_vertex_group_weights, assign_vertex_grp


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

    use_as_faceit_rig: BoolProperty(
        name='Use as Faceit Rig',
        default=False,
        description='Use this armature as the new Faceit rig for baking expressions. (Keep expressions active)',
    )

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            if context.scene.faceit_armature:
                if context.scene.faceit_body_armature and context.scene.faceit_body_armature_head_bone:
                    return True

    def invoke(self, context, event):
        scene = context.scene
        if not scene.faceit_shapes_generated and scene.faceit_expression_list:
            self.use_as_faceit_rig = True
        self.tag_arp_custom = self.is_arp_body = any([x.startswith('arp_') for x in scene.faceit_body_armature.keys()])

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'merge_faceit_weights', icon='MOD_VERTEX_WEIGHT')
        if self.merge_faceit_weights:
            row = layout.row()
            row.label(text='WARNING! Some Body Weights might be overwritten.')
        row = layout.row()
        row.prop(self, 'keep_faceit_bone_groups', icon='GROUP_BONE')
        row = layout.row()
        row.prop(self, 'use_as_faceit_rig', icon='ARMATURE_DATA')
        if self.is_arp_body:

            row = layout.row()
            row.label(text='Auto Rig Pro detected:')

            if 'c_eye_target.x' in context.scene.faceit_body_armature.pose.bones:
                row = layout.row()
                row.label(text='WARNING! ARP Face Rig detected. Consider Removing it.')

            row = layout.row()
            row.prop(self, 'tag_arp_custom', icon='EVENT_C')

    def cancel(self, context):
        bpy.ops.ed.undo()

    def execute(self, context):

        scene = context.scene

        # --------------- SCENE SETTINGS -----------------------
        # - Get all relevant settings and objects
        # ------------------------------------------------------

        auto_normalize = scene.tool_settings.use_auto_normalize
        scene.tool_settings.use_auto_normalize = False

        # Rigs
        body_rig = scene.faceit_body_armature
        faceit_rig = futils.get_faceit_armature(force_original=True)

        # Face parent bone
        head_bone = scene.faceit_body_armature_head_bone

        if not faceit_rig:
            self.report({'ERROR'}, 'The Faceit Armature doesn\'t exist')
            return{'CANCELLED'}

        # Unhide
        futils.set_hide_obj(body_rig, False)
        futils.set_hide_obj(faceit_rig, False)

        # Combined Rig layer status
        rig_layers_combined = [a or b for a, b in zip(faceit_rig.data.layers, body_rig.data.layers)]

        # The Bone Groups from Faceit Rig
        if self.keep_faceit_bone_groups:
            faceit_bone_groups = get_bone_groups_dict(faceit_rig)

        # Force default constraint values
        restore_constraints_to_default_values(faceit_rig)

        # Force Rest Position
        faceit_rig.data.pose_position = 'REST'
        body_rig.data.pose_position = 'REST'

        if self.tag_arp_custom:
            # Get all bone names for ARP custom tags
            all_faceit_bones = [b.name for b in faceit_rig.pose.bones]

        # Get faceit deform vertex groups names
        all_faceit_deform_groups = get_deform_bones_from_armature(faceit_rig)

        # --------------- MERGE WEIGHTS ------------------------
        # - Split individual surfaces of all bound objects
        # - Get all face weights in a single group (inverse of def-face)
        # - Normalize body weights, lock the new group
        # - transfer the new body weights back to the original
        # - Join the original objects
        # ------------------------------------------------------
        if self.merge_faceit_weights:

            # Get the relevant deform bones for both armatures
            all_body_deform_groups = get_deform_bones_from_armature(body_rig)

            # Remove Rigid group
            face_deform_groups = all_faceit_deform_groups.copy()
            face_deform_groups.remove('DEF-face')

            # Get all face objects that are bound to the faceit armature
            objects_to_process = [ob for ob in futils.get_faceit_objects_list() if any(
                [vg.name in all_faceit_deform_groups for vg in ob.vertex_groups])]

            if not objects_to_process:
                self.report({'ERROR'}, 'Please bind the armature first!')
                return {'CANCELLED'}

            print('processing {} objects'.format(len(objects_to_process)))

            vg_lock_state_dict = {}
            obj_mod_show_dict = {}

            split_objects_dict = {}  # Keep reference for all split objects to original
            split_objects_with_face_weights = []  # split objects to process

            for obj in objects_to_process:

                # Store vertex lock states
                vg_lock_state_dict[obj] = {vg.name: vg.lock_weight for vg in obj.vertex_groups}

                # Hide all modifiers
                for mod in obj.modifiers:

                    try:
                        obj_mod_show_dict[obj.name][mod.name] = mod.show_viewport
                    except KeyError:
                        obj_mod_show_dict[obj.name] = {mod.name: mod.show_viewport}

                    mod.show_viewport = False

                # Split the objects
                print('Start splitting {}'.format(obj.name))

                split_objects_dict[obj] = split_objects = split_object(obj)

                for s_obj in split_objects:

                    # Check if any faceit weights are on the object
                    if any([vg.name in face_deform_groups for vg in s_obj.vertex_groups]):
                        split_objects_with_face_weights.append(s_obj)
                        continue

                print('Done splitting {}'.format(obj.name))
            print('processing {} split objects'.format(len(split_objects_with_face_weights)))

            for obj in split_objects_with_face_weights:

                print('Start process on {}'.format(obj.name))

                dup_ob = futils.duplicate_obj(obj, link=True)

                def_face_grp_dup = dup_ob.vertex_groups.get('DEF-face')

                # Get the body weights to be normalized
                relevant_groups = all_body_deform_groups
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

                _data_transfer_vertex_groups(dup_ob, obj)

                # Remove the duplicate obj
                bpy.data.objects.remove(dup_ob)

            # Join objects back to original
            for obj, split_objects in split_objects_dict.items():

                print('join objects back together')

                futils.clear_object_selection()
                for s_obj in split_objects:
                    # debug_duplicate = s_obj.copy()
                    # debug_duplicate.data = s_obj.data.copy()
                    # context.scene.collection.objects.link(debug_duplicate)
                    # debug_duplicate.name = debug_duplicate.name + '_debug'
                    if s_obj:
                        futils.set_active_object(s_obj.name)

                futils.set_active_object(obj.name)
                bpy.ops.object.join()

                # Restore lock state
                lock_state = vg_lock_state_dict[obj]
                for vg_name, lock in lock_state.items():
                    vg = obj.vertex_groups.get(vg_name)
                    if vg:
                        vg.lock_weight = lock

                def_face_grp = obj.vertex_groups.get('DEF-face')
                if def_face_grp:
                    obj.vertex_groups.remove(def_face_grp)

        else:
            # Don't merge Faceit Weights --> Remove them
            for obj in futils.get_faceit_objects_list():
                for vg in obj.vertex_groups:
                    if vg.name in all_faceit_deform_groups:
                        obj.vertex_groups.remove(vg)

        # --------------- OBJECT SETTINGS -------------------
        # | - Remove Faceit Armature Mod
        # | - Restore Modifier Visibility States
        # | - Ensure Body Armature Mod
        # -------------------------------------------------------
        for obj in objects_to_process:
            found_body_armature_mod = False
            show_mod_dict = obj_mod_show_dict.get(obj.name)

            # Remove the Faceit armature modifier
            arm_mod = futils.get_faceit_armature_modifier(obj)
            if arm_mod:
                obj.modifiers.remove(arm_mod)

            # Restore the hide states of all other modifiers
            if show_mod_dict:
                for mod, show_value in show_mod_dict.items():
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
        head_bone = body_rig.data.edit_bones.get(head_bone)

        face_bone.parent = head_bone

        if self.keep_faceit_bone_groups:
            bpy.ops.object.mode_set(mode='POSE')
            set_bone_groups_from_dict(body_rig, bone_groups_dict=faceit_bone_groups)

        bpy.ops.object.mode_set()

        body_rig.data.layers = rig_layers_combined[:]

        if self.tag_arp_custom:
            for b in body_rig.pose.bones:
                if b.name in all_faceit_bones:
                    b['cc'] = 1.0

        # Restore POSE position
        body_rig.data.pose_position = 'POSE'

        # --------------- SCENE SETTINGS -------------------
        # - Set Faceit Armature if user choosed
        # ------------------------------------------------------

        if not body_rig.data.get('faceit_rig_id'):
            body_rig.data['faceit_rig_id'] = get_random_rig_id()

        if self.use_as_faceit_rig:
            scene.faceit_armature = body_rig
            if not scene.faceit_shapes_generated:
                faceit_action = bpy.data.actions.get('overwrite_shape_action')
                if getattr(body_rig, 'animation_data') and faceit_action:
                    # if getattr(body_rig.animation_data, 'action')
                    body_rig.animation_data.action = faceit_action
        else:
            scene.faceit_armature = None

        scene.tool_settings.use_auto_normalize = auto_normalize

        self.report({'INFO'}, 'Succesfully joined the FaceitRig to the armature {}'.format(body_rig.name))
        return{'FINISHED'}
