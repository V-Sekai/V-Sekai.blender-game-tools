import bpy
import platform
from pathlib import Path, PureWindowsPath
import mmap
from typing import List
import shutil
import os
import stat
import getpass
import subprocess


def select_only_one_object(obj: bpy.types.Object):
    for selected_obj in bpy.context.selected_objects:
        selected_obj.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def get_platform():
    current_platform = platform.system()

    if current_platform == "Darwin":
        current_platform = "MacOS"

    return current_platform

# Needed for updating Blender's native .fbx export and import to be compatible with dembones
def insert_code(file_path: Path, insert_location: str, line_to_find: str, code_to_insert: List):
    # op_system = get_platform()
    # if op_system == 'Windows':
    #     username = getpass.getuser()
    #     # win_path = str(PureWindowsPath(file_path.parent))
    #     command = r'icacls "' + str(file_path.parent) + r'" /grant:r "' + username + r'":(OI)(CI)MF'
    #     appcmd = subprocess.check_call(command)
    #     os.chmod(file_path, stat.S_IRWXO)
    # else:
    #     os.chmod(file_path, 0o777)

    print("file_path_0", file_path)

    with open(file_path, 'rb', 0) as file:
        s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        op_system = get_platform()
        if op_system == 'Windows':
            code_to_check = '\r\n'.join(code_to_insert)
        else:
            code_to_check = '\n'.join(code_to_insert)
        if s.find(bytes(code_to_check, encoding='utf-8')) != -1:
            return

    with open(file_path, 'r') as file:
        file_contents = file.read()
    
    lines = file_contents.splitlines()

    new_lines = []
    for line in lines:
        if line_to_find in line:
            if insert_location == "before":
                new_lines.extend(code_to_insert)
            new_lines.append(line)
            if insert_location == "after":
                new_lines.extend(code_to_insert)
        else:
            new_lines.append(line)
    
    return new_lines
    # os.chmod(file_path, stat.S_IRWXO)
    # os.chmod(file_path, 0o777)
    
    # with open(file_path, 'w') as file:
    #     file.write('\n'.join(new_lines))
    
    # os.chmod(file_path, 0o755)

def copy_files(src_dir: Path, dest_dir: Path, extensions: List[str]):
    for file_path in src_dir.iterdir():
        if file_path.is_file() and file_path.suffix in extensions:
            shutil.copy2(str(file_path), str(dest_dir))

def copy_presets(src_dir: Path, preset_subdir: Path):
    """Copy presets from `src_dir` to `presets_dir/preset_subdir`

    Args:
        src_dir (Path): Directory with presets .py files
        preset_subdir (Path): Subdir of Blender's preset directory
    """
    
    presets_dir = Path(bpy.utils.user_resource(resource_type='SCRIPTS', path="presets"))
    addon_presets_dir = presets_dir / preset_subdir

    if not addon_presets_dir.is_dir():
        addon_presets_dir.mkdir(parents=True, exist_ok=True)

    copy_files(src_dir, addon_presets_dir, ['.py'])

def append_collections(
    scene: bpy.types.Scene,
    filepath: str,
    collections_to_ignore: List = [],
):
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.collections = [
            name for name in data_from.collections if name not in collections_to_ignore
        ]

    for collection in data_to.collections:
        scene.collection.children.link(collection)

    return data_to.collections


def ensure_collections_appended(collections_data: List[dict]):
    for collection_data in collections_data:
        if not bpy.data.collections.get(collection_data["collection_name"]):
            append_collections(
                bpy.context.scene,
                str(collection_data["filepath"]),
                collection_data["collections_to_ignore"],
            )
            print(
                f"Collection {collection_data['collection_name']} doesn't exist. {collection_data['collection_name']} appended from {collection_data['filepath']}"
            )

def mute_shape_keys(obj: bpy.types.Object):
    if obj.data.shape_keys:
        for shape_key in obj.data.shape_keys.key_blocks:
            shape_key.mute = True