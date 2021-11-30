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


# Substance in Blender Load an SBSAR
# 5/27/2020
import bpy
import os
from bpy.props import BoolProperty, CollectionProperty, StringProperty
from bpy.types import Operator, OperatorFileListElement
from bpy_extras.io_utils import ImportHelper
from ..mainthread import PopCursor, PushCursor
from ..sbsarmanager import SbsarManager
from ..substancetoolsmanager import AreToolsInstalled
from ..ui.substanceutils import LoadSbsarFromUI

DIR_PATH = 'DIR_PATH'


class SUBSTANCE_OT_LoadSBSAR(Operator, ImportHelper):
    """Open file browser to select a Substance 3D material file"""
    bl_idname = 'substance.load_sbsar'
    bl_label = 'Load Substance Material'
    bl_enabled_description = 'Open file browser to select a Substance 3D material'
    bl_disabled_description = 'Please create an object for the material'
    bl_options = {'REGISTER'}
    description_arg: BoolProperty(options={'HIDDEN'})                       # noqa: F821
    filename_ext = '.sbsar'
    filter_glob: StringProperty(default='*.sbsar', options={'HIDDEN'})      # noqa: F722, F821
    files: CollectionProperty(name='Substance 3D material files', type=OperatorFileListElement)     # noqa: F722
    directory: StringProperty(subtype=DIR_PATH)

    def __init__(self):
        """ Clear out the file path """
        self.filepath = ''

    @classmethod
    def description(cls, context, properties):
        """ Change the help hint based on the conditions """
        if properties.description_arg is True:
            return SUBSTANCE_OT_LoadSBSAR.bl_enabled_description
        else:
            return SUBSTANCE_OT_LoadSBSAR.bl_disabled_description

    def execute(self, context):
        """ Execute the operator to select an SBSAR file """

        if len(self.files) < 1 or len(self.files[0].name) < 1:
            return {'FINISHED'}

        if not AreToolsInstalled():
            bpy.ops.substance.tools_not_installed('INVOKE_DEFAULT')
            return {'FINISHED'}

        #  load the file
        PushCursor('WAIT')
        loadedIds = []
        for f in self.files:
            fp = os.path.join(self.directory, f.name)
            print('load file:', fp)
            loadedId = LoadSbsarFromUI(fp, context, '')
            if loadedId.startswith('ERROR'):
                print('Failed to load: ' + fp)
            else:
                addon = bpy.context.preferences.addons['Substance3DInBlender']
                if addon.preferences.auto_create_materials:
                    sbsarData = SbsarManager.getSbsarDataFromId(loadedId)
                    sbsarData.autoCreateMat = True
                loadedIds.append(loadedId)
        for i in loadedIds:
            SbsarManager.renderSbsar(i)
        PopCursor()
        return {'FINISHED'}
