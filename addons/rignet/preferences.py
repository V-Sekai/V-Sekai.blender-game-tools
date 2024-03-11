import os
from pathlib import Path
import sys

import bpy

from .setup_utils import cuda_utils
from .setup_utils import venv_utils
from importlib.util import find_spec

import urllib.request
from zipfile import ZipFile

class BRIGNET_OT_DownloadExtract(bpy.types.Operator):
    """Operator to download and extract a file from a given URL"""
    bl_idname = "brignet.download_extract"
    bl_label = "Download and Extract"

    # Properties used by the operator to store information about the download and extraction
    url: bpy.props.StringProperty(
        name="URL",
        description="URL to download the file from"
    )
    
    target_directory: bpy.props.StringProperty(
        name="Target Directory",
        description="Directory where the downloaded file should be extracted"
    )
    
    file_name: bpy.props.StringProperty(
        name="File Name",
        description="Name of the file to be downloaded"
    )

    def execute(self, context):
        # Check if target directory exists, if not, create it
        if not os.path.exists(self.target_directory):
            os.makedirs(self.target_directory)

        # Full path to the downloaded zip file
        full_file_path = os.path.join(self.target_directory, self.file_name)
        
        # Download the file
        try:
            urllib.request.urlretrieve(self.url, full_file_path)
            self.report({'INFO'}, f"Downloaded file {self.file_name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to download file: {e}")
            return {'CANCELLED'}

        # Extracting the zip file
        try:
            with ZipFile(full_file_path, 'r') as zip_ref:
                zip_ref.extractall(self.target_directory)
            self.report({'INFO'}, f"Extracted file {self.file_name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to extract file: {e}")
            return {'CANCELLED'}
        
        # Optionally remove the zip file after extraction
        os.remove(full_file_path)
        
        return {'FINISHED'}

class BrignetEnvironment(bpy.types.Operator):
    """Create virtual environment with required modules"""
    bl_idname = "wm.brignet_environment"
    bl_label = "Create Remesh model from Collection"

    @classmethod
    def poll(cls, context):
        env_path = bpy.context.preferences.addons[__package__].preferences.modules_path
        if not env_path:
            return False

        return len(BrignetPrefs.missing_modules) > 0

    def execute(self, context):
        env_path = bpy.context.preferences.addons[__package__].preferences.modules_path
        venv_utils.setup_environment(env_path)
        BrignetPrefs.add_module_paths()
        return {'FINISHED'}


class BrignetPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    _cuda_info = None
    _added_paths = []
    missing_modules = []

    @staticmethod
    def check_cuda():
        BrignetPrefs._cuda_info = cuda_utils.CudaDetect()

    @staticmethod
    def add_module_paths():
        BrignetPrefs.reset_module_paths()
        env_path = bpy.context.preferences.addons[__package__].preferences.modules_path

        if not os.path.isdir(env_path):
            return False
            
        if sys.platform.startswith("linux"):
            lib_path = os.path.join(env_path, 'lib')
            sitepackages = os.path.join(lib_path, 'python3.7', 'site-packages')
        else:
            lib_path = os.path.join(env_path, 'Lib')
            sitepackages = os.path.join(lib_path, 'site-packages')

        if not os.path.isdir(sitepackages):
            # not a python path, but the user might be still typing
            return False

        platformpath = os.path.join(sitepackages, sys.platform)
        platformlibs = os.path.join(platformpath, 'lib')

        mod_paths = [lib_path, sitepackages, platformpath, platformlibs]
        if sys.platform.startswith("win"):
            mod_paths.append(os.path.join(env_path, 'DLLs'))
            mod_paths.append(os.path.join(sitepackages, 'Pythonwin'))

        for mod_path in mod_paths:
            if not os.path.isdir(mod_path):
                print(f'{mod_path} not a directory, skipping')
                continue
            if mod_path not in sys.path:
                print(f'adding {mod_path}')
                sys.path.append(mod_path)
                BrignetPrefs._added_paths.append(mod_path)

        BrignetPrefs.check_modules()
        return True

    @staticmethod
    def reset_module_paths():
        # FIXME: even if we do this, additional modules are still available
        for mod_path in BrignetPrefs._added_paths:
            print(f"removing module path: {mod_path}")
            sys.path.remove(mod_path)
        BrignetPrefs._added_paths.clear()

    def update_modules(self, context):
        self.add_module_paths()

    modules_path: bpy.props.StringProperty(
        name='RigNet environment path',
        description='Path to additional modules (torch, torch_geometric...)',
        subtype='DIR_PATH',
        update=update_modules,
        default=os.path.join(os.path.join(os.path.dirname(__file__)), '_additional_modules')
    )

    model_path: bpy.props.StringProperty(
        name='Model path',
        description='Path to RigNet code',
        subtype='DIR_PATH',
        default=os.path.join(os.path.join(os.path.dirname(__file__)), 'RigNet', 'checkpoints')
    )

    modules_found: bpy.props.BoolProperty(
        name='Required Modules',
        description="Whether required modules have been found or not"
    )

    @staticmethod
    def check_modules():
        BrignetPrefs.missing_modules.clear()
        for mod_name in ('torch', 'torch_geometric', 'torch_cluster', 'torch_sparse', 'torch_scatter', 'scipy'):
            if not find_spec(mod_name):
                BrignetPrefs.missing_modules.append(mod_name)

        preferences = bpy.context.preferences.addons[__package__].preferences
        preferences.modules_found = len(BrignetPrefs.missing_modules) == 0

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        box = layout.box()
        col = box.column(align=True)

        # Model Path Property
        row = col.row()
        split = row.split(factor=0.8, align=False)
        sp_col = split.column()
        sp_col.prop(self, 'model_path', text='Model Path')

        # Download Model Button
        if not os.path.isdir(self.model_path) or 'bonenet' not in os.listdir(self.model_path):
            sp_col = split.column()
            op = sp_col.operator(
                BRIGNET_OT_DownloadExtract.bl_idname,
                text='Download'
            )
            op.url = "https://github.com/V-Sekai/V-Sekai.rig_net/releases/download/0.0.1/trained_models.zip"
            op.target_directory = ".."
            op.file_name = "trained_models.zip"

            # Instructions for Unpacking Models
            row = col.row()
            if self.model_path:
                unpack_path = op.target_directory
                row.label(text="Please, unpack the content to")
                row = col.row()
                row.label(text=f"    {unpack_path}")
            else:
                row.label(text="Please, set 'Model Path' where 'RigNet' will be created and unpacked.")

        info = BrignetPrefs._cuda_info
        if info:
            py_ver = sys.version_info
            row = column.row()
            row.label(text=f"Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
            if info.result == cuda_utils.CudaResult.SUCCESS:
                row = column.row()
                row.label(text=f"Cuda Version: {info.major}.{info.minor}.{info.micro}")
            elif info.result == cuda_utils.CudaResult.NOT_FOUND:
                row = column.row()
                row.label(text="CUDA Toolkit not found", icon='ERROR')

                if info.has_cuda_hardware:
                    row = column.row()
                    split = row.split(factor=0.1, align=False)
                    split.column()
                    col = split.column()
                    col.label(text="CUDA hardware is present. Please make sure that CUDA Toolkit is installed")

                    op = col.operator(
                        'wm.url_open',
                        text='nVidia Downloads',
                        icon='URL'
                    )
                    op.url = 'https://developer.nvidia.com/downloads'
                row = column.row()
                row.label(text="Could not retrieve CUDA information", icon='ERROR')
                
                row = column.row()
                row.label(text="Please ensure CUDA Toolkit is installed if you have CUDA-compatible hardware")
                
                op = row.operator(
                    'wm.url_open',
                    text='Download CUDA Toolkit from NVIDIA',
                    icon='URL'
                )
                op.url = 'https://developer.nvidia.com/cuda-downloads'

        if self.missing_modules:
            row = column.row()
            row.label(text=f"Modules not found: {','.join(self.missing_modules)}", icon='ERROR')
