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


# Substance in Blender Menus and Panels
# 5/27/2020

import os
from bpy.path import native_pathsep
from bpy.types import Menu, Panel
from bpy.utils import previews
from ..sbsarmanager import SbsarManager
from ..ui.substanceutils import (SUBSTANCE_OT_CreateSbsar, SUBSTANCE_OT_DuplicateSbsar,
                                 SUBSTANCE_OT_RemoveButton, SUBSTANCE_OT_RefreshSbsar)
from ..actions.substancegotowebsite import SUBSTANCE_OT_GotoShare, SUBSTANCE_OT_GotoSource
from ..actions.substanceloadsbsar import SUBSTANCE_OT_LoadSBSAR


# load the custom icons
icons_dir = native_pathsep(os.path.join(os.path.dirname(__file__), "../icons"))
icons_dict = previews.new()
icons_dict.load("share_icon", os.path.join(icons_dir, "share.png"), 'IMAGE')
icons_dict.load("source_icon", os.path.join(icons_dir, "source.png"), 'IMAGE')


def UpdateTooltips(context, materialNeededOps, generalOps):
    """ Update operator tooltips based on being enabled or disabled """
    haveMaterialObject = False
    for obj in context.selected_objects:
        if hasattr(obj.data, 'materials'):
            haveMaterialObject = True
            break
    activeSbsar = SbsarManager.getActiveSbsarId()
    if len(activeSbsar) > 0:
        # update all operators that require a material
        for matOp in materialNeededOps:
            if haveMaterialObject:
                matOp.description_arg = True
            else:
                matOp.description_arg = False
        # update the rest of the operators
        for genOp in generalOps:
            genOp.description_arg = True
    else:
        # set all operators to false
        for matOp in materialNeededOps:
            matOp.description_arg = False
        for genOp in generalOps:
            genOp.description_arg = False


def SubstanceMenuFactory(space):

    class SUBSTANCE_MT_Main(Menu):
        bl_idname = 'SUBSTANCE_MT_%s' % space
        bl_space_type = space
        bl_label = 'Substance 3D Menu'
        bl_category = 'Substance 3D'

        def draw(self, context):
            """ Draw the Panel/Menu UI """
            self.layout.operator_context = 'INVOKE_REGION_WIN'
            actionCol = self.layout.column(align=True)
            actionCol.operator(SUBSTANCE_OT_LoadSBSAR.bl_idname).description_arg = True

            # Get the name of the active sbsar
            activeSbsarName = 'No SBSAR Selected'
            activeSbsarData = SbsarManager.getActiveSbsarData()
            if activeSbsarData:
                activeSbsarName = activeSbsarData.name

                # draw the action icon operators
                attachTxt = 'Attach: ' + activeSbsarName
                createOp = actionCol.operator(SUBSTANCE_OT_CreateSbsar.bl_idname, text=attachTxt)
                dupTxt = 'Duplicate: ' + activeSbsarName
                duplicateOp = actionCol.operator(SUBSTANCE_OT_DuplicateSbsar.bl_idname, text=dupTxt)
                sbsarData = SbsarManager.getActiveSbsarData()
                if sbsarData:
                    duplicateOp.file_path = sbsarData.file
                refreshTxt = 'Refresh: ' + activeSbsarName
                refreshOp = actionCol.operator(SUBSTANCE_OT_RefreshSbsar.bl_idname, text=refreshTxt)
                removeTxt = 'Remove: ' + activeSbsarName
                removeOp = actionCol.operator(SUBSTANCE_OT_RemoveButton.bl_idname, text=removeTxt)

                # Update the tool tips for operators which can be disabled
                UpdateTooltips(context, [createOp], [duplicateOp, refreshOp, removeOp])

    return SUBSTANCE_MT_Main


def SubstancePanelFactory(space):

    class SUBSTANCE_PT_Main(Panel):
        bl_idname = 'SUBSTANCE_PT_%s' % space
        bl_space_type = space
        bl_label = 'Substance 3D Panel'
        bl_region_type = 'UI'
        bl_category = 'Substance 3D'

        def draw(self, context):
            """ Draw the Panel/Menu UI """
            global icons_dict
            self.layout.label(text='(Quick Access: Ctrl+Shift+U)')
            actionRow = self.layout.row(align=True)

            # draw action operators
            actionRow.operator(SUBSTANCE_OT_LoadSBSAR.bl_idname, text='Load').description_arg = True
            actionRow.separator()
            createOp = actionRow.operator(SUBSTANCE_OT_CreateSbsar.bl_idname, text='Apply')
            actionRow.separator()

            # draw icon operators
            actionRow.operator(SUBSTANCE_OT_GotoShare.bl_idname, text='',
                               icon_value=icons_dict["share_icon"].icon_id)
            actionRow.separator()
            actionRow.operator(SUBSTANCE_OT_GotoSource.bl_idname, text='',
                               icon_value=icons_dict["source_icon"].icon_id)
            actionRow.separator()
            duplicateOp = actionRow.operator(SUBSTANCE_OT_DuplicateSbsar.bl_idname, text='', icon='DUPLICATE')
            actionRow.separator()
            sbsarData = SbsarManager.getActiveSbsarData()
            if sbsarData:
                duplicateOp.file_path = sbsarData.file
            refreshOp = actionRow.operator(SUBSTANCE_OT_RefreshSbsar.bl_idname, text='', icon='FILE_REFRESH')
            actionRow.separator()
            removeOp = actionRow.operator(SUBSTANCE_OT_RemoveButton.bl_idname, text='', icon='TRASH')

            # Update the tool tips for operators which can be disabled
            UpdateTooltips(context, [createOp], [duplicateOp, refreshOp, removeOp])

            # draw loaded sbsars
            if len(context.scene.loadedSbsars) > 0:
                # the sbsar list only displays properly in the panel
                col = self.layout.column()
                col.label(text='Loaded SBSARs')
                col.template_list('SUBSTANCE_UL_SBSARDisplayList', 'Loaded SBSAR(s)', context.scene,
                                  'loadedSbsars', context.scene, 'sbsar_index')

    return SUBSTANCE_PT_Main
