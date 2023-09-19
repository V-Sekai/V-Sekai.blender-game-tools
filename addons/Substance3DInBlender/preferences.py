"""
Copyright (C) 2022 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# file: preferences.py
# brief: Addon Preferences
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy


from .api import SUBSTANCE_Api

from .props.utils import get_shader_presets, get_bitdepths
from .props.shader import SUBSTANCE_PG_ShaderPreset
from .props.common import SUBSTANCE_PG_Tiling, SUBSTANCE_PG_Resolution
from .props.shortcuts import SUBSTANCE_PG_Shortcuts

from .ops.toolkit import SUBSTANCE_OT_UninstallTools, SUBSTANCE_OT_UpdateTools, SUBSTANCE_OT_InstallTools
from .ops.web import SUBSTANCE_OT_GetTools, SUBSTANCE_OT_GotoDocs, SUBSTANCE_OT_GotoForums, SUBSTANCE_OT_GotoDiscord
from .ops.shader import SUBSTANCE_OT_ResetShaderPreset

from .utils import SUBSTANCE_Utils
from .common import (
    Code_ShaderParmType,
    Code_OutParms,
    IMAGE_EXPORT_FORMAT,
    DRAW_DEFAULT_FACTOR,
    ADDON_PACKAGE,
    PATH_DEFAULT,
    TOOLKIT_EXPECTED_VERSION,
    PATH_LIBARY_DEFAULT,
    COLORSPACES_DICT
)


class SUBSTANCE_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_PACKAGE

    tiling: bpy.props.PointerProperty(
        name="tiling",
        description="The default tiling to be used in the shader network", # noqa
        type=SUBSTANCE_PG_Tiling)
    resolution: bpy.props.PointerProperty(
        name="resolution",
        description="The default resolution to be used in the substance", # noqa
        type=SUBSTANCE_PG_Resolution)
    normal_format: bpy.props.EnumProperty(
        name="normal_format",
        default="OpenGL", # noqa
        description="The default normal format", # noqa
        items=[("OpenGL", "OpenGL", ""), ("DirectX", "DirectX", "")]) # noqa

    auto_attach_material: bpy.props.BoolProperty(
        name='Automatically append the material', # noqa
        default=False,
        description='Automatically append the substance material to the selected object(s) when loaded') # noqa
    auto_highlight_sbsar: bpy.props.BoolProperty(
        name='Automatically highlight the material for selected objects', # noqa
        default=True,
        description='When an object is selected in the 3D view automatically update the loaded Substance 3D Material') # noqa

    cycles_autoupdate_enabled: bpy.props.BoolProperty(
        name='Cycles Auto-update textures', # noqa
        default=False,
        description='Force reload textures when updated in cycles') # noqa
    path_relative_sbsar_enabled: bpy.props.BoolProperty(
        name='Auto-package sbsar files on save', # noqa
        default=False,
        description='Copy the loaded sbsar files to the defined relative path when you save the blend file') # noqa

    path_library: bpy.props.StringProperty(
        name='Sbsar library path', # noqa
        default=PATH_LIBARY_DEFAULT,
        subtype='DIR_PATH', # noqa
        description='Open by default this path when loading an Substance file (*.sbsar)') # noqa
    path_default: bpy.props.StringProperty(
        name='Temporary Path', # noqa
        default=PATH_DEFAULT,
        subtype='DIR_PATH', # noqa
        description='Path used for temporary exports of the material texture maps') # noqa
    path_relative_sbsar: bpy.props.StringProperty(
        name='Relative path for Substance files', # noqa
        default="sbsar/", # noqa
        description='When saved, copy the substance file to this relative path in order to pack the project') # noqa
    path_relative_tx: bpy.props.StringProperty(
        name='Relative path for texture files', # noqa
        default="substance tx/$matname", # noqa
        description='When saved copy the texture files to this relative path in order to pack the project') # noqa

    shader_preset_list: bpy.props.EnumProperty(
        name="shader_preset_list",
        description="The available shader network presets", # noqa
        items=get_shader_presets)
    shader_presets: bpy.props.CollectionProperty(type=SUBSTANCE_PG_ShaderPreset)

    export_format: bpy.props.EnumProperty(
        name="export_format",
        default="1",
        description="The image export format for input parameters", # noqa
        items=IMAGE_EXPORT_FORMAT)

    output_default_colorspace: bpy.props.EnumProperty(
        name="output_default_colorspace",
        default="Non-Color", # noqa
        description="The default colorspace to be used when creating the shader network", # noqa
        items=COLORSPACES_DICT)
    output_default_format: bpy.props.EnumProperty(
        name="output_default_format",
        default="tga", # noqa
        description="The default file format to be used by the Output", # noqa
        items=SUBSTANCE_Utils.get_formats())
    output_default_bitdepth: bpy.props.EnumProperty(
        name="output_default_bitdepth",
        default=0,
        description="The default bitdepth of the Output", # noqa
        items=lambda self, context: get_bitdepths(self, context,  "output_default_format"))

    shortcuts: bpy.props.PointerProperty(type=SUBSTANCE_PG_Shortcuts)

    collapse_shader_parms: bpy.props.BoolProperty(default=True)
    collapse_shader_outputs: bpy.props.BoolProperty(default=True)
    collapse_shortcuts: bpy.props.BoolProperty(default=True)

    def draw(self, context):
        _col = self.layout.column(align=True)

        _, _toolkit_version = SUBSTANCE_Api.toolkit_version_get()
        if _toolkit_version is not None and _toolkit_version in TOOLKIT_EXPECTED_VERSION:
            _col.label(text='Thank you for installing the Substance 3D Integration Tools. {}'.format(_toolkit_version))
            _row = _col.row()
            _row.operator(SUBSTANCE_OT_UninstallTools.bl_idname, text='Uninstall Tools', icon='TRASH')
            _row.operator(SUBSTANCE_OT_UpdateTools.bl_idname, text='Update Tools', icon='FILEBROWSER')
        elif _toolkit_version is not None and _toolkit_version not in TOOLKIT_EXPECTED_VERSION:
            _col.alert = True
            _msg = 'Update Needed! Please download and install a compatible Integration tool version: [{}] '.format(
                " , ".join(TOOLKIT_EXPECTED_VERSION))
            _col.label(text=_msg)
            _col.alert = False
            _row = _col.row()
            _row.operator(SUBSTANCE_OT_GetTools.bl_idname, text='Download', icon='URL')
            _row.operator(SUBSTANCE_OT_UpdateTools.bl_idname, text='Update Tools', icon='FILEBROWSER')
            return
        else:
            _col.alert = True
            _msg = 'Please download and install Integration Tools, a separate module for Adobe Substance 3D'
            _col.label(text=_msg)
            _col.alert = False
            _row = _col.row()

            _row.operator(SUBSTANCE_OT_GetTools.bl_idname, text='Download', icon='URL')
            _row.operator(SUBSTANCE_OT_InstallTools.bl_idname, text='Install from disk', icon='FILEBROWSER')
            return

        _row = _col.row()
        _row.label(text="")

        # Docs
        _row = _col.row()
        _row.label(text="")
        _row = _col.row()
        _row.label(text="Help & Resources:")
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _col_1.alignment = "RIGHT"
        _col_1.label(text="Documentation")
        _col_2.operator(SUBSTANCE_OT_GotoDocs.bl_idname, text='Documentation', icon='URL')
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _col_1.alignment = "RIGHT"
        _col_1.label(text="Forums")
        _col_2.operator(SUBSTANCE_OT_GotoForums.bl_idname, text='Forums', icon='URL')
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _col_1.alignment = "RIGHT"
        _col_1.label(text="Discord Sever")
        _col_2.operator(SUBSTANCE_OT_GotoDiscord.bl_idname, text='Discord Server', icon='URL')

        # Options
        _row = _col.row()
        _row.label(text="")
        _row = _col.row()
        _row.label(text="Defaults:")

        # Tiling
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="Tiling")
        _row = _col_2.row()
        _row.prop(self.tiling, "x", text='')
        _row_2 = _row.column()
        _row_2.prop(self.tiling, "y", text='')
        _row_2.enabled = not self.tiling.linked
        _row_3 = _row.column()
        _row_3.prop(self.tiling, "z", text='')
        _row_3.enabled = not self.tiling.linked
        _row.prop(self.tiling, "linked", text='', icon='LOCKED')

        # Resolution
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="Resolution")
        _row = _col_2.row()
        _row.prop(self.resolution, "width", text='')
        _row_2 = _row.column()
        _row_2.prop(self.resolution, "height", text='')
        _row_2.enabled = not self.resolution.linked
        _row.prop(self.resolution, "linked", text='', icon='LOCKED')

        # Normal Format
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="Normal Format")
        _row = _col_2.row()
        _row.prop(self, "normal_format", text='')

        # Export Image Format
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="Export Image Format")
        _row = _col_2.row()
        _row.prop(self, "export_format", text='')

        # Options
        _row = _col.row()
        _row.label(text="")
        _row = _col.row()
        _row.label(text="Automations:")

        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_2.row()
        _col_2.prop(self, 'auto_attach_material')
        _row = _col_2.row()
        _row.prop(self, 'auto_highlight_sbsar')
        _row = _col_2.row()
        _row.prop(self, 'cycles_autoupdate_enabled')

        # Paths
        _row = _col.row()
        _row.label(text="")
        _row = _col.row()
        _row.label(text="Paths:")

        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="SBSAR Library Path")
        _row = _col_2.row()
        _row.prop(self, "path_library", text='')

        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="Temporary Folder")
        _row = _col_2.row()
        _row.prop(self, "path_default", text='')

        _row = _col.row()
        _row.label(text="")
        _row = _col.row()
        _row.label(text="Relative Paths:")

        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="Copy [*.sbsar] files on save to")
        _row = _col_2.row()
        _row.prop(self, 'path_relative_sbsar_enabled', text="")
        _row = _row.row()
        _row.enabled = self.path_relative_sbsar_enabled
        _row.prop(self, "path_relative_sbsar", text="")

        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="On save, copy textures to")
        _row = _col_2.row()
        _row.prop(self, "path_relative_tx", text='')

        _row = _col.row()
        _row.label(text="")

        # Options
        _row = _col.row()
        _row.label(text="")
        _row = _col.row()
        _row.label(text="Shader Networks:")

        # Show current shader preset
        _selected_preset_idx = int(self.shader_preset_list)
        _selected_preset = self.shader_presets[_selected_preset_idx]
        _modified = "(*)" if _selected_preset.modified else ""
        # Shader Presets
        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()
        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="Shader Preset" + _modified)
        _row = _col_2.row()
        _row.prop(self, "shader_preset_list", text="")
        _row.operator(SUBSTANCE_OT_ResetShaderPreset.bl_idname, text="", icon="LOOP_BACK")

        _row = _col.row()
        _row.label(text="")

        # Shader preset parameters
        if len(_selected_preset.parms) != 0:
            _row = _col.row()
            _row.alignment = "LEFT"
            _row.prop(
                self,
                "collapse_shader_parms",
                icon='TRIA_DOWN' if self.collapse_shader_parms else 'TRIA_RIGHT',
                text="Parameters:",
                emboss=False)
            if self.collapse_shader_parms:
                _parms = getattr(context.scene, _selected_preset.parms_class_name)
                for _idx, _parm in enumerate(_selected_preset.parms):
                    _row = _col.row()
                    _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
                    _col_1 = _split.column()
                    _col_2 = _split.column()
                    _row = _col_1.row()
                    _row.alignment = "RIGHT"
                    _row.label(text=_parm.label)
                    _row = _col_2.row()

                    if _parm.type == Code_ShaderParmType.float_maxmin.value:
                        _row.prop(_parms, _parm.name, text="")
                    elif _parm.type == Code_ShaderParmType.float_slider.value:
                        _row.prop(_parms, _parm.name, text="", slider=True)
                    else:
                        _row.label(text="Parameter not supported yet")
                _row = _col.row()
                _row.label(text="")

        # Shader preset outputs
        _row = _col.row()
        _row.alignment = "LEFT"
        _row.prop(
            self,
            "collapse_shader_outputs",
            icon='TRIA_DOWN' if self.collapse_shader_outputs else 'TRIA_RIGHT',
            text="Outputs:",
            emboss=False)
        if self.collapse_shader_outputs:
            _outputs = getattr(context.scene, _selected_preset.outputs_class_name)
            for _idx, _output in enumerate(_selected_preset.outputs):
                _row = _col.row()
                _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
                _col_1 = _split.column()
                _col_2 = _split.column()
                _row = _col_1.row()
                _row.alignment = "RIGHT"
                _row.label(text=_output.label)
                _row = _col_2.row()
                _row.prop(_outputs, _output.name + Code_OutParms.enabled.value, text="")
                _row.prop(_outputs, _output.name + Code_OutParms.colorspace.value, text="")
                _row.prop(_outputs, _output.name + Code_OutParms.format.value, text="")
                _row.prop(_outputs, _output.name + Code_OutParms.bitdepth.value, text="")

            _row = _col.row()
            _row.label(text="")

            _row = _col.row()
            _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
            _col_1 = _split.column()
            _col_2 = _split.column()
            _row = _col_1.row()
            _row.alignment = "RIGHT"
            _row.label(text="Generic Output")
            _row = _col_2.row()
            _row.separator()
            _row.separator()
            _row.prop(self, "output_default_colorspace", text="")
            _row.prop(self, "output_default_format", text="")
            _row.prop(self, "output_default_bitdepth", text="")

        # Shortcuts
        _row = _col.row()
        _row.label(text="")
        _row = _col.row()
        _row.label(text="Shortcuts:")

        _row = _col.row()
        _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
        _col_1 = _split.column()
        _col_2 = _split.column()

        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text="")
        _row = _col_2.row()
        _row.label(text="CTRL")
        _row.label(text="SHIFT")
        _row.label(text="ALT")
        _row.label(text="KEY")

        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text=self.shortcuts.menu_name)
        _row = _col_2.row()
        _split = _row.split(factor=0.25)
        _col_3 = _split.column()
        _row = _col_3.row()
        _row.prop(self.shortcuts, 'menu_ctrl', text="")
        _col_4 = _split.column()
        _row = _col_4.row()
        _row.prop(self.shortcuts, 'menu_shift', text="")
        _col_5 = _split.column()
        _row = _col_5.row()
        _row.prop(self.shortcuts, 'menu_alt', text="")
        _col_6 = _split.column()
        _row = _col_6.row()
        _row.prop(self.shortcuts, 'menu_key', text="")

        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text=self.shortcuts.load_name)
        _row = _col_2.row()
        _split = _row.split(factor=0.25)
        _col_3 = _split.column()
        _row = _col_3.row()
        _row.prop(self.shortcuts, 'load_ctrl', text="")
        _col_4 = _split.column()
        _row = _col_4.row()
        _row.prop(self.shortcuts, 'load_shift', text="")
        _col_5 = _split.column()
        _row = _col_5.row()
        _row.prop(self.shortcuts, 'load_alt', text="")
        _col_6 = _split.column()
        _row = _col_6.row()
        _row.prop(self.shortcuts, 'load_key', text="")

        _row = _col_1.row()
        _row.alignment = "RIGHT"
        _row.label(text=self.shortcuts.apply_name)
        _row = _col_2.row()
        _split = _row.split(factor=0.25)
        _col_3 = _split.column()
        _row = _col_3.row()
        _row.prop(self.shortcuts, 'apply_ctrl', text="")
        _col_4 = _split.column()
        _row = _col_4.row()
        _row.prop(self.shortcuts, 'apply_shift', text="")
        _col_5 = _split.column()
        _row = _col_5.row()
        _row.prop(self.shortcuts, 'apply_alt', text="")
        _col_6 = _split.column()
        _row = _col_6.row()
        _row.prop(self.shortcuts, 'apply_key', text="")

        _row = _col_2.row()
        _row.label(text="*Shortcut updates need a restart in order to be applied.")

        _row = _col.row()
        _row.label(text="")
