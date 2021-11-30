"""
Copyright (C) 2021 Adobe.
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


# Substance in Blender Set Data Path
# 1/11/2021
import bpy


class SUBSTANCE_OT_SetDataPath(bpy.types.Operator):
    """Browse to set the substance data cache folder"""
    bl_idname = 'substance.set_data_path'
    bl_label = 'Set Data Folder'
    bl_options = {'REGISTER'}
    bl_enabled_description = 'Set a relative path from the .blend file to store generated data'
    bl_disabled_description = 'The .blend file must be saved before setting the relative path'
    description_arg: bpy.props.BoolProperty()
    filter_folder: bpy.props.BoolProperty(default=True, options={'HIDDEN'})  # noqa: F821

    # Define this to tell 'fileselect_add' that we want a directoy
    directory: bpy.props.StringProperty(
        name='Data Path',                                       # noqa: F722
        description='Location of stored substance data')        # noqa: F722

    @classmethod
    def description(cls, context, properties):
        if properties.description_arg is True:
            return SUBSTANCE_OT_SetDataPath.bl_enabled_description
        else:
            return SUBSTANCE_OT_SetDataPath.bl_disabled_description

    def execute(self, context):
        """Set the data cache folder"""
        # back out of the .blend name folder and then strip the beginning // from bpy.path.relpath
        relativePath = "../" + bpy.path.relpath(self.directory, start=None)[2:]
        context.preferences.addons['Substance3DInBlender'].preferences.data_path = relativePath
        return {'FINISHED'}

    def invoke(self, context, event):
        """Invoke Data Cache Folder Browse"""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
