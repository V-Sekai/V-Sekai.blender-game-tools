import bpy
import subprocess
from pathlib import Path
import time
from typing import List
from .utils import select_only_one_object, get_platform, ensure_collections_appended, insert_code, mute_shape_keys
import addon_utils
from bpy.types import Operator
from bl_operators.presets import AddPresetBase
import os

# class DEMBONES_OT_info(Operator):
#     """Print some info"""

#     bl_label = "Execute"
#     bl_idname = "dembones.info_msg"
#     bl_options = {"REGISTER"}

#     def execute(self, context: bpy.types.Context):
#         self.report({"ERROR"}, context.scene.dembones.info_msg)
#         return {"FINISHED"}

class DEMBONES_OT_execute(Operator):
    """Execute DemBones"""

    bl_label = "Execute"
    bl_idname = "dembones.execute"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    def execute(self, context: bpy.types.Context):
        context.window_manager.progress_begin(0, 100)
        fbx_update = self._update_fbx_import_export()
        if fbx_update == {"CANCELLED"}:
            return {"CANCELLED"}
        self.current_platform: str = get_platform()
        self.add_ons_dir: Path = Path(addon_utils.paths()[1])
        self.add_on_name: str = Path(__file__).resolve().parent.name
        self.dembones_bin: Path = list(
            Path(f"{self.add_ons_dir / self.add_on_name}/dembones/{self.current_platform}").glob("*")
        )[0]
        if not os.access(self.dembones_bin, os.X_OK):
            os.chmod(self.dembones_bin, 0o755)
        self.selected_mesh_abc = None
        self.selected_mesh_fbx = None
        self.selected_armature = None
        self.dembones_result_fbx_name = "dembones_result.fbx"
        self.intermediate_files_path = Path(bpy.context.preferences.addons[__package__].preferences.intermediate_files)
        if not self.intermediate_files_path.exists():
            self.intermediate_files_path.mkdir(parents=True, exist_ok=True)

        self.log_path = Path(bpy.context.preferences.addons[__package__].preferences.log).parent
        if not self.log_path.exists():
            self.log_path.mkdir(parents=True, exist_ok=True)

        # Check for correct selection of input data
        inputs_ok = self._set_mesh_and_armature(context)

        # \n2. One mesh object and one armature object
        if not inputs_ok:
            self.report(
                {"ERROR"},
                "Incorrect selection! Possible selection options: \n1. One mesh object \n2. One mesh object and one armature object which drives it, plus target deformation mesh object",
            )
            return {"CANCELLED"}

        self.abc_path = (self.intermediate_files_path
            / f"{self.selected_mesh_abc.name}.abc")
        self.fbx_path = (self.intermediate_files_path
            / f"{self.selected_mesh_abc.name}.fbx")
        
        # Clear previous exports if they exist
        self._clear_previous_exports(context)
        
        # Export alembic
        self._export_abc(context, self.abc_path)

        # Export .fbx
        self._export_fbx(context, self.fbx_path)

        # run the binary file using subprocess.Popen
        self._run_dembones(context)

        # Import .fbx
        self._import_fbx(context)

        # Mute shape keys of imported mesh
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                mute_shape_keys(obj)

        # end the progress bar
        context.window_manager.progress_update(100)
        context.window_manager.progress_end()

        return {"FINISHED"}
    
    def _clear_previous_exports(self, context: bpy.types.Context):
        fbx_path = Path(self.intermediate_files_path) / self.dembones_result_fbx_name
        fbx_path.unlink(missing_ok=True)
        self.abc_path.unlink(missing_ok=True)
        self.fbx_path.unlink(missing_ok=True)

    def _set_mesh_and_armature(self, context: bpy.types.Context):
        """Ensure that either 2 objects are selected (one mesh and one armature type),
        or only one mesh object is selected
        """
        context.window_manager.progress_update(10)

        selected_objects = bpy.context.selected_objects
        inputs_ok = False
        # # check if 2 objects are selected (one mesh and one armature type) or only one mesh object is selected
        if len(selected_objects) == 2:
            if (
                selected_objects[0].type == "MESH"
                and selected_objects[1].type == "ARMATURE"
            ):
                self.selected_mesh_abc = selected_objects[0]
                self.selected_mesh_fbx = selected_objects[0]
                self.selected_armature = selected_objects[1]
                inputs_ok = True
            elif (
                selected_objects[0].type == "ARMATURE"
                and selected_objects[1].type == "MESH"
            ):
                self.selected_mesh_abc = selected_objects[1]
                self.selected_mesh_fbx = selected_objects[1]
                self.selected_armature = selected_objects[0]
                inputs_ok = True

        if len(selected_objects) == 1:
            if selected_objects[0].type == "MESH":
                self.selected_mesh_abc = selected_objects[0]
                self.selected_mesh_fbx = selected_objects[0]
                self.selected_armature = None
                inputs_ok = True
        elif len(selected_objects) == 3:
            mesh_objects = [obj for obj in selected_objects if obj.type == "MESH"]
            armature_objects = [obj for obj in selected_objects if obj.type == "ARMATURE"]

            children_of_selected_armature = []
            if len(mesh_objects) == 2 and len(armature_objects) == 1:
                self.selected_armature = armature_objects[0]
                for obj in mesh_objects:
                    if self.selected_armature in [mod.object for mod in obj.modifiers if mod.type == 'ARMATURE']:
                        children_of_selected_armature.append(obj)
                if len(children_of_selected_armature) == 1:
                    self.selected_mesh_fbx = children_of_selected_armature[0]
                    mesh_objects.remove(children_of_selected_armature[0])
                    self.selected_mesh_abc = mesh_objects[0]
                    inputs_ok = True

        return inputs_ok

    def _export_abc(self, context: bpy.types.Context, filepath: Path):
        context.window_manager.progress_update(20)

        select_only_one_object(self.selected_mesh_abc)
        
        bpy.ops.wm.alembic_export(
            filepath=str(filepath),
            selected=True,
        )

        return filepath

    def _export_fbx(self, context: bpy.types.Context, filepath: Path):
        context.window_manager.progress_update(30)

        select_only_one_object(self.selected_mesh_fbx)
        if self.selected_armature:
            self.selected_armature.select_set(True)
        
        bpy.ops.export_scene.fbx(
            filepath=str(filepath),
            use_selection=True,
            use_custom_props=True,
            global_scale=0.01,
            add_leaf_bones=False,
            bake_anim_simplify_factor=0,
            use_armature_deform_only=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
        )

        return filepath
    
    def _import_fbx(self, context: bpy.types.Context):
        context.window_manager.progress_update(70)
        fbx_path = f"{Path(self.intermediate_files_path) / self.dembones_result_fbx_name}"

        actions_names_before_import = {action.name for action in bpy.data.actions}

        bpy.ops.import_scene.fbx(filepath=fbx_path,
                                 global_scale=100,
                                 anim_offset=0)
        
        actions_names_after_import = {action.name for action in bpy.data.actions}

        new_action_names = actions_names_after_import - actions_names_before_import
        
        if len(new_action_names) == 2:
            for obj in bpy.context.selected_objects:
                if obj.type == 'ARMATURE':
                    active_action_name = {obj.animation_data.action.name}
                    break
            action_name_to_apply = new_action_names - active_action_name
            action_to_apply = action_name_to_apply.pop()
            obj.animation_data.action = bpy.data.actions[action_to_apply]


    def _run_dembones(self, context: bpy.types.Context):
        args = [
            self.dembones_bin,
            f"--abc={self.abc_path}",
            f"--init={self.fbx_path}",
            f"--out={Path(self.intermediate_files_path) / self.dembones_result_fbx_name}",
            f"--nBones={context.scene.dembones.n_bones}",
            f"--nInitIters={context.scene.dembones.n_init_iters}",
            f"--nIters={context.scene.dembones.n_iters}",
            f"--tolerance={context.scene.dembones.tolerance}",
            f"--patience={context.scene.dembones.patience}",
            f"--nTransIters={context.scene.dembones.n_trans_iters}",
            f"--bindUpdate={context.scene.dembones.bind_update}",
            f"--transAffine={context.scene.dembones.trans_affine}",
            f"--transAffineNorm={context.scene.dembones.trans_affine_norm}",
            f"--nWeightsIters={context.scene.dembones.n_weights_iters}",
            f"--nnz={context.scene.dembones.nnz}",
            f"--weightsSmooth={context.scene.dembones.weights_smooth}",
            f"--weightsSmoothStep={context.scene.dembones.weights_smooth_step}",
            f"--dbg={bpy.context.preferences.addons[__package__].preferences.dbg}",
            f"--log={bpy.context.preferences.addons[__package__].preferences.log}",
        ]

        process = subprocess.Popen(args)
        while process.poll() is None:
            context.window_manager.progress_update(50)

    def _update_fbx_import_export(self):
        fbx_files_changed_path = Path(__file__).parent / "fbx_files_changed"
        with open(fbx_files_changed_path, "r") as f:
            self.fbx_files_changed = f.read()
        
        if self.fbx_files_changed == "0":
            add_ons_dir: Path = Path(addon_utils.paths()[0])

            export_file_path = add_ons_dir / 'io_scene_fbx' / 'export_fbx_bin.py'

            updated_file = insert_code(export_file_path,
                        "after",
                        '        list_val = getattr(v, "to_list", lambda: None)()',
                        ['        if k in ["demLock", "lockInfluenceWeights"]:', '            elem_props_set(props, "p_bool", k.encode(), v, custom=True)', '            continue'])


            print('updated_file_0', updated_file)
            if updated_file:
                try:
                    with open(export_file_path, 'w') as file:
                        file.write('\n'.join(updated_file))
                    with open(fbx_files_changed_path, "w") as file:
                        self.fbx_files_changed = file.write("1")
                except:
                    self.report({"ERROR"}, "Please, run Blender as Administrator and click Execute button. \
                        \nYou need to do this only once",)
                    return {"CANCELLED"}
            else:
                with open(fbx_files_changed_path, "w") as file:
                    self.fbx_files_changed = file.write("1")

            import_file_path = add_ons_dir / 'io_scene_fbx' / 'import_fbx.py'

            updated_file = insert_code(import_file_path,
                        "before",
                        '                for skin_uuid, skin_link in fbx_connection_map.get(cluster_uuid):',
                        ['                if not fbx_connection_map.get(cluster_uuid):', '                    continue'])

            print('updated_file_1', updated_file)
            if updated_file:
                try:
                    with open(import_file_path, 'w') as file:
                        file.write('\n'.join(updated_file))
                    with open(fbx_files_changed_path, "w") as file:
                        self.fbx_files_changed = file.write("1")
                except:
                    self.report({"ERROR"}, "Please, run Blender as Administrator and click Execute button. \
                        \nYou need to do this only once",)
                    return {"CANCELLED"}
            else:
                with open(fbx_files_changed_path, "w") as file:
                    self.fbx_files_changed = file.write("1")

class DEMBONES_OT_set_dem_lock(Operator):
    """Add `demLock` custom attribute to selected pose bones"""

    bl_label = "Set demLock"
    bl_idname = "dembones.set_dem_lock"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        self.active_obj = context.view_layer.objects.active

        # Legacy marking of demLock bones with objects
        #
        # if not bpy.data.collections.get('dembones_demLock_visuals'):
            # collections_to_append = [
            #     {
            #         "collection_name": "dembones_demLock_visuals",
            #         "filepath": Path(__file__).parent / 'resources/demLock.blend',
            #         "collections_to_ignore": ["template"],
            #     }
            # ]

            # ensure_collections_appended(collections_to_append)

            # for collection_name in collections_to_append[0]["collections_to_ignore"]:
            #     collection = bpy.context.view_layer.layer_collection.children[
            #             "dembones_demLock_visuals"
            #         ].children[collection_name]
            #     collection.exclude = True
        
        if not self.active_obj.mode == 'POSE' and not self.active_obj.type == 'ARMATURE':
            self.report(
                {"ERROR"},
                "Please set the Armature to Pose mode and selecte at least one pose bone",
            )
            return {"CANCELLED"}

        else:
            bone_groups = self.active_obj.pose.bone_groups

            # create demLock bone group
            group_name = "demLock"
            if group_name not in bone_groups:
                demLock_bone_group = bone_groups.new(name=group_name)
                demLock_bone_group.color_set = 'THEME01'

            for bone in bpy.context.selected_pose_bones:
                if not bone.get('demLock'):
                    # Legacy marking of demLock bones with objects
                    #
                    # demlock_visual_template = bpy.data.objects['demLock']
                    # demlock_visual_new = demlock_visual_template.copy()
                    # demlock_visual_new.name = 'demLock_' + bone.name
                    # bpy.data.collections["dembones_demLock_visuals"].objects.link(demlock_visual_new)
                    # demlock_visual_new.parent = self.active_obj
                    # demlock_visual_new.parent_type = 'BONE'
                    # demlock_visual_new.parent_bone = bone.name
                    # demlock_visual_new.matrix_world = self.active_obj.matrix_world @ bone.matrix
                    # bone['lockInfluenceWeights'] = 1

                    if not bone.get('dembones_original_bone_group'):
                        if bone.bone_group:
                            bone['dembones_original_bone_group'] = bone.bone_group.name
                    bone.bone_group = bone_groups[group_name]

                    bone['demLock'] = 1

            bpy.context.view_layer.update()
        return {"FINISHED"}

class DEMBONES_OT_delete_dem_lock(Operator):
    """Delete `demLock` custom attribute of selected pose bones"""

    bl_label = "Delete demLock"
    bl_idname = "dembones.delete_dem_lock"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        self.active_obj = context.view_layer.objects.active
        
        if not self.active_obj.mode == 'POSE' and not self.active_obj.type == 'ARMATURE':
            self.report(
                {"ERROR"},
                "Please set the Armature to Pose mode and selecte at least one pose bone",
            )
            return {"CANCELLED"}

        else:
            bone_groups = self.active_obj.pose.bone_groups
            for bone in bpy.context.selected_pose_bones:
                if bone.get('demLock'):
                    del(bone['demLock'])

                    original_bone_group = bone.get('dembones_original_bone_group')
                    if original_bone_group:
                        bone.bone_group = bone_groups.get(original_bone_group)
                        del(original_bone_group)
                    else:
                        bone.bone_group = None

                    # Legacy marking of demLock bones with objects
                    #
                    # del(bone['lockInfluenceWeights'])
                    # bpy.data.objects.remove(bpy.data.objects.get('demLock_' + bone.name))
            bpy.context.view_layer.update()
        return {"FINISHED"}

class DEMBONES_OT_settings_preset_add(AddPresetBase, Operator):
    '''Add/Remove DemBones settings template'''
    bl_idname = "dembones.settings_preset_add"
    bl_label = "Add/Remove DemBones settings template"
    preset_menu = "DEMBONES_MT_display_presets"

    # variable used for all preset values
    preset_defines = [
        "dembones = bpy.context.scene.dembones"
    ]

    # properties to store in the preset
    preset_values = [
        "dembones.n_bones",
        "dembones.n_init_iters",
        "dembones.n_iters",
        "dembones.tolerance",
        "dembones.patience",
        "dembones.n_trans_iters",
        "dembones.bind_update",
        "dembones.trans_affine",
        "dembones.trans_affine_norm",
        "dembones.n_weights_iters",
        "dembones.nnz",
        "dembones.weights_smooth",
        "dembones.weights_smooth_step",
        "dembones.dbg",
        "dembones.intermediate_files",
        "dembones.log",
    ]

    # where to store the preset
    preset_subdir = "blender_dembones"

