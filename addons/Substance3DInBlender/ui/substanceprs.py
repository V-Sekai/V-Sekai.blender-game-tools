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


# Substance SBSPRS file support
# 07/21/2020
import bpy
import os
import xml.etree.ElementTree as ET
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator
from ..sbsarmanager import SbsarManager


def ShowMessageBox(message="", title="Title", icon='INFO'):
    """ Show a message box to the user """
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def RefreshParamList(context):
    """ Trigger the parameter window to be rebuilt with the preset parameters """
    SbsarManager.sbsarParamMgr.unregister()
    context.scene.sbsar_index = context.scene.sbsar_index


def SetCurrentPreset(sbsarData, name):
    """ Update the current Preset value """
    paramMgr = SbsarManager.sbsarParamMgr
    propClassName = paramMgr.getPropClassName('Graph Parameters', paramMgr.propertySuffix, sbsarData.id[-4:])
    SbsarManager.sbsarParamMgr.setProperty(propClassName, 'Preset', name)


def WritePresetToNewFile(filepath, sbsarData, selectedPreset):
    """ Write the created preset to the file """
    root = ET.Element('sbspresets')
    root.set('formatversion', '1.1')
    root.set('count', '1')
    AddPresetToRoot(filepath, root, sbsarData, selectedPreset)
    tree = ET.ElementTree(root)
    tree.write(filepath)


def AddPresetToFile(filepath, sbsarData, preset):
    """ Add a specific preset to the preset file """
    tree = ET.parse(filepath)
    root = tree.getroot()

    # check if this preset already exists
    for child in root:
        if child.get('label') == preset:
            bpy.ops.substance.confirm_sbsprs_overwrite('INVOKE_DEFAULT', filepath=filepath, name=preset)
            return

    # add the preset
    AddPresetToRoot(filepath, root, sbsarData, preset)
    tree.write(filepath)


def AddPresetToRoot(filepath, root, sbsarData, preset):
    """ Add a preset as the subelement to the root node """
    pgk = ET.SubElement(root, 'sbspreset')
    pgk.set('pkgurl', sbsarData.name)
    pgk.set('label', preset)
    presetValue = sbsarData.presets[preset].split(": ' ")[1]
    presetValues = presetValue.split("\\n")
    for pValue in presetValues:
        if pValue.startswith("  <presetinput"):
            pValue = pValue.lstrip()
            pValueLength = len(pValue)

            # strip off the leading < and the ending >/ characters
            pValue = pValue[1:pValueLength-3]
            ET.SubElement(pgk, pValue)


def RemovePresetFromFile(filepath, name):
    """ Remove a preset from the file """
    rewriteFile = False
    tree = ET.parse(filepath)
    root = tree.getroot()
    for child in root:
        if child.get('label') == name:
            root.remove(child)
            rewriteFile = True

    # if we remove atleast one child rewrite to the file
    if rewriteFile:
        tree.write(filepath)


def SavePreset(context, sbsarData, name):
    """ Save the custom preset as a new preset with the name given """
    presetValue = sbsarData.presets['Custom']
    presetValue = presetValue.replace('label=""', 'label="' + name + '"')
    sbsarData.presets[name] = presetValue
    sbsarData.addedPresetNames.append(name)

    # disable updating the engine parameter values when saving a preset
    SbsarManager.allowPresetChange(False)
    sbsarIndex = bpy.context.scene.loadedSbsars.find(sbsarData.name)
    if sbsarIndex < 0:
        print('Sbsar data is not in the blend file')
    else:
        presetIndex = context.scene.loadedSbsars[sbsarIndex].blenderPresets.find(name)
        if presetIndex < 1:
            presetData = context.scene.loadedSbsars[sbsarIndex].blenderPresets.add()
        else:
            presetData = context.scene.loadedSbsars[sbsarIndex].blenderPresets[presetIndex]
        presetData.name = name
        presetData.value = sbsarData.presets[name]
        context.scene.loadedSbsars[sbsarIndex].presetName = name
        presetData.isResolutionLinked = SbsarManager.sbsarParamMgr.getResolutionLinkValue(sbsarData)

    RefreshParamList(context)
    SetCurrentPreset(sbsarData, name)
    SbsarManager.allowPresetChange(True)


def LoadSBSPRSFile(context, filepath):
    """ Verify the file being passed in and then load the data """
    filename, extension = os.path.splitext(filepath)
    if extension == '.sbsprs':
        sbsarData = SbsarManager.getActiveSbsarData()
        msg = LoadSBSPRS(context, filepath, sbsarData)
        RefreshParamList(context)

        # Show the user the outcome of loading the file
        ShowMessageBox(msg, 'Loaded SBSPRS File')
    else:
        print('Presets must be loaded from a .sbsprs file not: ' + extension)
    return {'FINISHED'}


def LoadSBSPRS(context, file, sbsarData):
    """ Parse the SBSARPRS file data """
    addedPresets = 'No new presets were found.'
    if sbsarData:
        root = ET.parse(file).getroot()
        count = 0
        for child in root:
            label = 'UnDefined'
            if 'label' in child.attrib:
                label = child.get('label')
            presetValue = ET.tostring(child, encoding='unicode', method='xml')
            if label not in sbsarData.presets:
                # store in the active data to update the UI list
                sbsarData.presets[label] = str({'label': label, 'value': ' ' + presetValue})

                # determine if the resolution values are linked
                isLinked = True
                try:
                    for gc in child:
                        if 'identifier' in gc.attrib:
                            if gc.attrib['identifier'] == '$outputsize':
                                val = gc.attrib['value'].split(',', 1)
                                if val[0] != val[1]:
                                    isLinked = False
                except Exception:
                    pass

                # store the preset with the .blend file
                sbsarIndex = bpy.context.scene.loadedSbsars.find(sbsarData.name)
                if sbsarIndex < 0:
                    print('Preset file does not correspond to loaded sbsar')
                else:
                    presetIndex = context.scene.loadedSbsars[sbsarIndex].blenderPresets.find(label)
                    if presetIndex < 1:
                        presetData = context.scene.loadedSbsars[sbsarIndex].blenderPresets.add()
                    else:
                        presetData = context.scene.loadedSbsars[sbsarIndex].blenderPresets[presetIndex]
                    presetData.name = label
                    presetData.value = sbsarData.presets[label]
                    presetData.isResolutionLinked = isLinked
                    sbsarData.addedPresetNames.append(label)
                    if count == 0:
                        addedPresets = 'Added: ' + label
                    else:
                        addedPresets = addedPresets + ', ' + label
                    count += 1
    else:
        print('No sbsar to attach presets to')
    return addedPresets


class SUBSTANCE_OT_LoadPresetFile(Operator):
    """Load a known sbsprs file"""
    bl_idname = 'substance.load_preset_file'
    bl_label = 'load a known sbsprs file'
    bl_description = 'load a known sbsprs file'
    bl_options = {'REGISTER'}
    filepath: StringProperty()

    def execute(self, context):
        return LoadSBSPRSFile(context, self.filepath)

    def invoke(self, context, event):
        return self.execute(context)


class SUBSTANCE_OT_LoadSBSPRS(Operator, ImportHelper):
    bl_idname = 'substance.load_sbsprs'
    bl_label = 'Load SBSPRS File'
    bl_description = 'Add presets from the selected sbsprs file'
    bl_options = {'REGISTER'}
    filename_ext = '.sbsprs'
    filter_glob: StringProperty(default='*.sbsprs', options={'HIDDEN'})      # noqa: F722, F821

    def __init__(self):
        """ Clear out the file path """
        self.filepath = ''

    def execute(self, context):
        """ Execute the operator to select an SBSAR file """
        return LoadSBSPRSFile(context, self.filepath)


class SUBSTANCE_OT_NameSBSPRS(Operator):
    bl_idname = "substance.name_sbsprs"
    bl_label = ''
    bl_description = 'Save current parameters as a preset'
    sbsprsName: StringProperty(name="Preset Name")                          # noqa: F722

    def execute(self, context):
        if len(self.sbsprsName) > 0:
            bpy.ops.substance.save_sbsprs('INVOKE_DEFAULT', saveName=self.sbsprsName)
            self.sbsprsName = ''
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.alignment = 'CENTER'
        col = layout.column()
        col.prop(self, 'sbsprsName')


class SUBSTANCE_OT_SaveSBSPRS(Operator):
    bl_idname = 'substance.save_sbsprs'
    bl_label = 'Save SBSPRS to a file'
    bl_description = 'Save current custom preset to a file'
    bl_options = {'REGISTER'}
    saveName: StringProperty()

    def execute(self, context):
        """ Execute the operator to select an SBSAR file """
        sbsarData = SbsarManager.getActiveSbsarData()
        if self.saveName in sbsarData.addedPresetNames:
            bpy.ops.substance.confirm_preset_overwrite('INVOKE_DEFAULT', name=self.saveName)
        else:
            SavePreset(context, sbsarData, self.saveName)
        return {'FINISHED'}


class SUBSTANCE_ConfirmPresetOverwrite(Operator):
    """ Confirm Overwrite SBSPRS file """
    bl_idname = "substance.confirm_preset_overwrite"
    bl_label = "Click OK to overwrite the presetor elsewhere to cancel"
    bl_options = {'REGISTER', 'INTERNAL'}
    name: StringProperty()

    def execute(self, context):
        sbsarData = SbsarManager.getActiveSbsarData()
        sbsarData.addedPresetNames.remove(self.name)
        SavePreset(context, sbsarData, self.name)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=325)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text='Preset name: ' + self.name)


class SUBSTANCE_ConfirmSBSPRSOverwrite(Operator):
    """ Confirm Overwrite SBSPRS file """
    bl_idname = "substance.confirm_sbsprs_overwrite"
    bl_label = "Click OK to overwrite the preset in this file"
    bl_options = {'REGISTER', 'INTERNAL'}
    filepath: StringProperty()
    name: StringProperty()

    def execute(self, context):
        sbsarSavedData = context.scene.loadedSbsars[context.scene.sbsar_index]
        RemovePresetFromFile(self.filepath, self.name)
        AddPresetToFile(self.filepath, SbsarManager.getActiveSbsarData(), sbsarSavedData.presetName)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=325)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text=self.filepath)


class SUBSTANCE_OT_ExportSBSPRSFile(Operator):
    bl_idname = 'substance.export_sbsprs_file'
    bl_label = 'Export Selected Preset to file'
    bl_description = 'Export the selected preset to the given file'
    bl_options = {'REGISTER'}
    filepath: StringProperty()
    presetName: StringProperty()

    def execute(self, context):
        """ Execute the operator to select an SBSAR file """
        if len(self.filepath) > 0:
            sbsarData = SbsarManager.getActiveSbsarData()
            if not os.path.exists(self.filepath):
                WritePresetToNewFile(self.filepath, sbsarData, self.presetName)
            elif os.path.isfile(self.filepath):
                AddPresetToFile(self.filepath, sbsarData, self.presetName)
        return {'FINISHED'}


class SUBSTANCE_OT_ExportSBSPRS(Operator, ImportHelper):
    bl_idname = 'substance.export_sbsprs'
    bl_label = 'Export Selected Preset'
    bl_enabled_description = 'Export the selected preset to a file'
    bl_disabled_description = 'Can only export a saved preset'
    bl_options = {'REGISTER'}
    description_arg: bpy.props.BoolProperty(options={'HIDDEN'})         # noqa: F821

    def __init__(self):
        """ Clear out the file path """
        self.filepath = ''

    @classmethod
    def description(cls, context, properties):
        if properties.description_arg is True:
            return SUBSTANCE_OT_ExportSBSPRS.bl_enabled_description
        else:
            return SUBSTANCE_OT_ExportSBSPRS.bl_disabled_description

    def execute(self, context):
        """ Execute the operator to select an SBSAR file """
        sbsarSavedData = context.scene.loadedSbsars[context.scene.sbsar_index]
        sbsarData = SbsarManager.getActiveSbsarData()
        if not os.path.exists(self.filepath):
            self.filepath += '.sbsprs'
            WritePresetToNewFile(self.filepath, sbsarData, sbsarSavedData.presetName)
        elif os.path.isfile(self.filepath):
            AddPresetToFile(self.filepath, sbsarData, sbsarSavedData.presetName)
        return {'FINISHED'}


class SUBSTANCE_OT_ConfirmDelete(Operator):
    bl_idname = 'substance.confirm_delete'
    bl_label = "Click OK to delete the current preset"

    def execute(self, context):
        sbsarData = SbsarManager.getActiveSbsarData()
        if sbsarData:
            # clear out the current preset and set to default
            sbsar = context.scene.loadedSbsars[context.scene.sbsar_index]
            name = sbsar.presetName
            sbsar.blenderPresets.remove(sbsar.blenderPresets.find(name))
            sbsar.presetName = 'Default'
            SetCurrentPreset(sbsarData, sbsar.presetName)
            sbsarData.removePreset(name)
            RefreshParamList(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)


class SUBSTANCE_OT_DeletePreset(Operator):
    bl_idname = 'substance.delete_preset'
    bl_label = 'Delete the selected preset'
    bl_enabled_description = 'Delete the selected preset'
    bl_disabled_description = 'Cannot delete embedded presets'
    bl_options = {'REGISTER'}
    description_arg: bpy.props.BoolProperty(options={'HIDDEN'})         # noqa: F821

    @classmethod
    def description(cls, context, properties):
        if properties.description_arg is True:
            return SUBSTANCE_OT_DeletePreset.bl_enabled_description
        else:
            return SUBSTANCE_OT_DeletePreset.bl_disabled_description

    def execute(self, context):
        bpy.ops.substance.confirm_delete('INVOKE_DEFAULT')
        return {'FINISHED'}
