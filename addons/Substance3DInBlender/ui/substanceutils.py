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


# Substance in Blender UI utilities
# 9/18/2020
import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator, UIList
from random import randint
from ..mainthread import PopCursor
from ..sbsarmanager import SbsarManager, SbsarRenderListener

MAX_RANDOM_SEED = 32767


def LoadSbsarFromUI(path, context, duplicateId):
    """ Load an SBSubstance 3D material from the UI File Browser """
    sbsarId = SbsarManager.loadSbsar(path, context, False, 'Default', duplicateId)
    if sbsarId.startswith('ERROR'):
        if 'timed out' in sbsarId:
            bpy.ops.substance.engine_timeout('INVOKE_DEFAULT')
        elif 'incompatible' in sbsarId:
            bpy.ops.substance.sbsar_no_output('INVOKE_DEFAULT')
        elif 'not installed' in sbsarId:
            bpy.ops.substance.tools_not_installed('INVOKE_DEFAULT')
        else:
            bpy.ops.substance.engine_error('INVOKE_DEFAULT')
        PopCursor()
        return 'ERROR'
    else:
        return sbsarId


class SUBSTANCE_OT_ErrorBase(Operator):
    bl_idname = 'substance.error_base'
    bl_label = 'Substance Error'

    def execute(self, context):
        self.report({'WARNING'}, self.bl_label)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class SUBSTANCE_OT_EngineError(SUBSTANCE_OT_ErrorBase):
    bl_idname = 'substance.engine_error'
    bl_label = 'Could not connect to Substance 3D Remote Engine'


class SUBSTANCE_OT_SbsarNoOutputError(SUBSTANCE_OT_ErrorBase):
    bl_idname = 'substance.sbsar_no_output'
    bl_label = 'Substance 3D material has no mapped outputs, update texture mapping'


class SUBSTANCE_OT_EngineTimeout(SUBSTANCE_OT_ErrorBase):
    bl_idname = 'substance.engine_timeout'
    bl_label = 'Engine timed out loading the desired Substance 3D material'


class SUBSTANCE_OT_ToolsNotInstalled(SUBSTANCE_OT_ErrorBase):
    bl_idname = 'substance.tools_not_installed'
    bl_label = 'Install Substance 3D Integration Tools from preferences'


class SUBSTANCE_OT_DuplicateSbsar(Operator, SbsarRenderListener):
    bl_idname = 'substance.duplicate_sbsar'
    bl_label = 'Duplicate Selected Substance 3D material'
    bl_enabled_description = 'Load a new instance of the selected Substance 3D material'
    bl_disabled_description = 'Must have a Substance 3D material selected to be duplicated'
    currentIDBeingDuplicated = ''
    description_arg: BoolProperty()
    file_path: StringProperty()

    @classmethod
    def description(cls, context, properties):
        if properties.description_arg is True:
            return SUBSTANCE_OT_DuplicateSbsar.bl_enabled_description
        else:
            return SUBSTANCE_OT_DuplicateSbsar.bl_disabled_description

    @classmethod
    def poll(cls, context):
        if len(SbsarManager.getActiveSbsarId()) > 0:
            return len(cls.currentIDBeingDuplicated) < 1
        return False

    @classmethod
    def onRenderComplete(cls, sbsarId):
        """ If the duplicated ID has rendered re-enable the duplicate button by clearing out the id """
        if sbsarId == SUBSTANCE_OT_DuplicateSbsar.currentIDBeingDuplicated:
            SUBSTANCE_OT_DuplicateSbsar.currentIDBeingDuplicated = ''
            SbsarManager.removeRenderListener(SUBSTANCE_OT_DuplicateSbsar)

    def execute(self, context):
        sbsarId = LoadSbsarFromUI(self.file_path, context, SbsarManager.getActiveSbsarId())
        if sbsarId.startswith('ERROR'):
            PopCursor()
            ret = {'CANCELLED'}
        else:
            SbsarManager.addRenderListener(SUBSTANCE_OT_DuplicateSbsar)
            SUBSTANCE_OT_DuplicateSbsar.currentIDBeingDuplicated = sbsarId
            SbsarManager.renderSbsar(sbsarId)
            ret = {'FINISHED'}
        return ret


class SUBSTANCE_OT_RemoveButton(Operator):
    bl_idname = 'substance.remove_sbsar'
    bl_label = 'Remove Selected Substance 3D material'
    bl_enabled_description = 'Remove the selected Substance 3D material'
    bl_disabled_description = 'Must have a Substance 3D material selected to remove'
    description_arg: BoolProperty()

    @classmethod
    def description(cls, context, properties):
        if properties.description_arg is True:
            return SUBSTANCE_OT_RemoveButton.bl_enabled_description
        else:
            return SUBSTANCE_OT_RemoveButton.bl_disabled_description

    @classmethod
    def poll(cls, context):
        return len(SbsarManager.getActiveSbsarId()) > 0

    def execute(self, context):
        SbsarManager.removeActiveSbsar()
        return {'FINISHED'}


class SUBSTANCE_OT_CreateSbsar(Operator):
    bl_idname = 'substance.create_material'
    bl_label = 'Attach Substance 3D material'
    bl_enabled_description = 'Attach the selected Substance 3D material to the selected object(s)'
    bl_disabled_description = 'Must have a Substance 3D material selected and atleast one object selected in the scene'
    description_arg: BoolProperty()
    sbsar_id: StringProperty()

    @classmethod
    def description(cls, context, properties):
        if properties.description_arg is True:
            return SUBSTANCE_OT_CreateSbsar.bl_enabled_description
        else:
            return SUBSTANCE_OT_CreateSbsar.bl_disabled_description

    @classmethod
    def poll(cls, context):
        haveMaterialObject = False
        for obj in context.selected_objects:
            if hasattr(obj.data, 'materials'):
                haveMaterialObject = True
                break
        return len(SbsarManager.getActiveSbsarId()) > 0 and haveMaterialObject

    def execute(self, context):
        sbsarData = SbsarManager.getSbsarDataFromId(self.sbsar_id)
        if not sbsarData:
            sbsarData = SbsarManager.getActiveSbsarData()
        selected_objects = [o for o in bpy.context.scene.objects if o.select_get()]
        for obj in selected_objects:
            if hasattr(obj.data, 'materials') and hasattr(SbsarManager.sbsarRenderCallback, 'preferences'):
                if sbsarData.mat is None:
                    mapping = SbsarManager.sbsarRenderCallback.preferences.principled_mapping
                    sbsarData.mat = SbsarManager.createMaterial(context, mapping, obj, sbsarData)
                else:
                    obj.data.materials.append(sbsarData.mat)
        return {'FINISHED'}


class SUBSTANCE_OT_RefreshSbsar(Operator, SbsarRenderListener):
    bl_idname = 'substance.refresh_material'
    bl_label = 'Refresh the Substance 3D material'
    bl_enabled_description = 'Reload the Substance 3D material'
    bl_disabled_description = 'Must have a Substance 3D material selected'
    currentIDBeingRefreshed = ''
    description_arg: BoolProperty()

    @classmethod
    def description(cls, context, properties):
        if properties.description_arg is True:
            return SUBSTANCE_OT_RefreshSbsar.bl_enabled_description
        else:
            return SUBSTANCE_OT_RefreshSbsar.bl_disabled_description

    @classmethod
    def poll(cls, context):
        if len(SbsarManager.getActiveSbsarId()) > 0:
            return len(cls.currentIDBeingRefreshed) < 1
        return False

    @classmethod
    def onRenderComplete(cls, sbsarId):
        """ If the refresh ID has rendered re-enable the refresh button by clearing out the id """
        if sbsarId == SUBSTANCE_OT_RefreshSbsar.currentIDBeingRefreshed:
            SUBSTANCE_OT_RefreshSbsar.currentIDBeingRefreshed = ''
            SbsarManager.removeRenderListener(SUBSTANCE_OT_RefreshSbsar)

    def execute(self, context):
        newId = SbsarManager.refreshCurrentSbsar(context)
        SUBSTANCE_OT_RefreshSbsar.currentIDBeingRefreshed = newId
        if len(newId) > 0:
            SbsarManager.addRenderListener(SUBSTANCE_OT_RefreshSbsar)
            SbsarManager.renderSbsar(newId)

            # Trigger the parameter window to be rebuilt with the preset parameters
            context.scene.sbsar_index = context.scene.sbsar_index
        return {'FINISHED'}


class SUBSTANCE_UL_SBSARDisplayList(UIList):
    """List to show all the loaded SBSARs."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='')


class SUBSTANCE_OT_RandomizeSeed(Operator):
    bl_idname = 'substance.randomize_seed'
    bl_label = 'Randomize'
    bl_description = 'Generate a new random value for the current SBSAR randomseed parameter'

    def execute(self, context):
        value = randint(0, MAX_RANDOM_SEED)
        SbsarManager.updateActiveRandomSeed(value)
        return {'FINISHED'}


class SUBSTANCE_OT_LoadFile(Operator):
    """Load a known sbsar file"""
    bl_idname = 'substance.load_file'
    bl_label = 'load a known sbsar file'
    bl_description = 'load a known sbsar file'
    bl_options = {'REGISTER'}
    filepath: StringProperty()

    def execute(self, context):
        SbsarManager.loadSbsar(self.filepath, context, False, 'Default', '')
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)
