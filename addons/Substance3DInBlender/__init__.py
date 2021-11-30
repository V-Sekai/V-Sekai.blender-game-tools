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

# Substance 3D in Blender Add On
# 5/01/2020
bl_info = {
    'name': 'Adobe Substance 3D add-on for Blender',
    'author': 'Adobe Inc.',
    'location': 'Node Editor Toolbar -- Shift-Ctrl-U',
    'version': (0, 14, 7),
    'blender': (2, 90, 0),
    'description': 'Adobe Substance 3D add-on for Blender',
    'tracker_url': "https://www.adobeprerelease.com/beta/68A24EE2-2EA8-416F-D95B-23B8E64E5DE8",
    'category': 'Node',
}

# bl_info drives the version number for the entire build
# however the bpy module is only defined when running in Blender
try:
    import atexit
    import bpy
    from bpy.app.handlers import persistent
    from bpy.types import AddonPreferences, PropertyGroup
    from bpy.props import BoolProperty, CollectionProperty, IntProperty, PointerProperty, StringProperty
    from .actions.substancegotowebsite import SUBSTANCE_OT_GotoShare, SUBSTANCE_OT_GotoSource, SUBSTANCE_OT_GetTools
    from .actions.substanceloadsbsar import SUBSTANCE_OT_LoadSBSAR
    from .actions.substancedatapath import SUBSTANCE_OT_SetDataPath
    from .keymap import Keymap
    from .mainthread import ExecuteQueuedFunction, PopCursor, PushCursor
    from .sbsardata import CopyDataFolder, GetDataFolder, GetTempDataFolder
    from .sbsarmanager import RunUIUpdateOutput, SetDefaultAndCustomPreset, SbsarManager
    from .substancetoolsmanager import (SUBSTANCE_OT_InstallTools, SUBSTANCE_OT_UpdateTools,
                                        SUBSTANCE_OT_UninstallTools, AreToolsInstalled, StartTools, StopTools,
                                        GetVersion)
    from .ui.nodegraph import SbsarOutputLink
    from .ui.parammanager import SUBSTANCE_MT_ExtendedPresetOptions
    from .ui.substancemenus import SubstanceMenuFactory, SubstancePanelFactory
    from .ui.substanceutils import (SUBSTANCE_OT_CreateSbsar, SUBSTANCE_OT_DuplicateSbsar,
                                    SUBSTANCE_OT_ErrorBase, SUBSTANCE_OT_EngineError,
                                    SUBSTANCE_OT_SbsarNoOutputError, SUBSTANCE_OT_EngineTimeout,
                                    SUBSTANCE_OT_RemoveButton, SUBSTANCE_UL_SBSARDisplayList,
                                    SUBSTANCE_OT_RandomizeSeed, SUBSTANCE_OT_ToolsNotInstalled,
                                    SUBSTANCE_OT_LoadFile, SUBSTANCE_OT_RefreshSbsar)
    from .ui.substanceprs import (SUBSTANCE_OT_LoadSBSPRS, SUBSTANCE_OT_NameSBSPRS, SUBSTANCE_OT_SaveSBSPRS,
                                  SUBSTANCE_OT_ExportSBSPRS, SUBSTANCE_OT_DeletePreset, SUBSTANCE_OT_ConfirmDelete,
                                  SUBSTANCE_ConfirmSBSPRSOverwrite, SUBSTANCE_ConfirmPresetOverwrite,
                                  SUBSTANCE_OT_LoadPresetFile, SUBSTANCE_OT_ExportSBSPRSFile)
    from .shaders.Principled_BSDF import PrincipledBDSFPreferences

    # is the blend file still loading sbsars
    ReloadingSBSARs = False

    @atexit.register
    def on_exit():
        StopTools()

    # re-register a function guarenteed to run on the main thread
    bpy.app.timers.register(ExecuteQueuedFunction)

    class ExternalPresetData(PropertyGroup):
        """ Preset data that is stored with the blend file """
        name: StringProperty(name='name', description='The name of the preset')                         # noqa: F722
        value: StringProperty(name='value', description='The value of the preset')                      # noqa: F722
        isResolutionLinked: BoolProperty(default=True, description='Is the resolution linked')          # noqa: F722

    class LoadedSbsars(PropertyGroup):
        """ The data saved with the blend file """
        name: StringProperty(name='name', description='The name of the Substance 3D material')          # noqa: F722
        id: StringProperty(name='id', description='The tools id of the Substance 3D material')          # noqa: F722
        filepath: StringProperty(name='filepath', description='The path to the Substance 3D material')  # noqa: F722
        customDisabledOutputs: StringProperty(name='customDisabledOutputs',
                                              description='comma separated list of disabled outputs')   # noqa: F722
        presetName: StringProperty(name='presetName', description='Preset name')                        # noqa: F722
        blenderPresets: CollectionProperty(type=ExternalPresetData)

        def getPropertyFromIdValue(self, id):
            """ Return the sbsar property given the sbsar ID """
            for i, sbsar in enumerate(bpy.types.scene.loadedSbsars):
                if id == self.id:
                    return sbsar
            return None

    class Substance3DInBlender(AddonPreferences):
        """ The Substance Plugin Preferences """
        bl_idname = __name__
        keymap = Keymap()

        # principle shader mapping
        show_principled_lists: BoolProperty(
            name=PrincipledBDSFPreferences.button_name,
            default=PrincipledBDSFPreferences.button_default_value,
            description=PrincipledBDSFPreferences.button_desc
        )
        data_path: StringProperty(
            name='Relative Data Path',                                          # noqa: F722
            description='Location of generated substance assets relative \
            to the .blend file.  Unsaved blend files will always save \
            these assets to the temporary directory')                           # noqa: F722
        auto_create_materials: BoolProperty(
            name='Automatically attach materials to selected objects',          # noqa: F722
            default=False,
            description='When a Substance 3D material is loaded automatically create \
                a Blender material for all selected objects')                   # noqa: F722
        show_hotkey_list: BoolProperty(
            name='Show Hotkey List',                                            # noqa: F722
            default=False,
            description='Expand this box into a list of all the hotkeys \
                for functions in this addon')                                   # noqa: F722
        hotkey_list_filter: StringProperty(
            name='Filter by Name',                                              # noqa: F722
            description='Show only hotkeys that have this text \
                in their name')                                                 # noqa: F722
        principled_mapping: PointerProperty(type=PrincipledBDSFPreferences)

        def draw(self, context):
            """ Draw the preference menu """
            layout = self.layout
            col = layout.column()
            if AreToolsInstalled():
                col.label(text='Thank you for installing the Substance 3D Integration Tools. ' + GetVersion())
                row = col.row()
                row.operator(SUBSTANCE_OT_UninstallTools.bl_idname, text='Uninstall Tools', icon='TRASH')
                row.operator(SUBSTANCE_OT_UpdateTools.bl_idname, text='Update Tools', icon='FILEBROWSER')
                col.separator()
                col.separator()
                col.prop(self, 'auto_create_materials')
                row = col.row(align=True)
                row.prop(self, 'data_path')
                if len(bpy.context.blend_data.filepath) < 1:
                    row.operator(SUBSTANCE_OT_SetDataPath.bl_idname, icon='FILE_FOLDER',
                                 text='').description_arg = False
                    row.enabled = False
                else:
                    row.operator(SUBSTANCE_OT_SetDataPath.bl_idname, icon='FILE_FOLDER',
                                 text='').description_arg = True
                    row.enabled = True
                col.prop(self, PrincipledBDSFPreferences.prop_name,
                         text=PrincipledBDSFPreferences.prop_text,
                         toggle=True)
                if self.show_principled_lists:
                    for prop_name in self.principled_mapping.__annotations__:
                        if prop_name == 'displacementScale':
                            row = col.row()
                            sp = row.split(factor=0.24)
                            sp.label(text='Displacement Scale:')
                            sp.prop(self.principled_mapping, prop_name,  text='', expand=True)
                        else:
                            col.prop(self.principled_mapping, prop_name)

                Substance3DInBlender.keymap.draw(self, layout)
            else:
                col.alert = True
                msg = 'Please download and install Integration Tools, a separate module for Adobe Substance 3D'
                col.label(text=msg)
                col.alert = False
                row = col.row()
                row.operator(SUBSTANCE_OT_GetTools.bl_idname, text='Download', icon='URL')
                row.operator(SUBSTANCE_OT_InstallTools.bl_idname, text='Install from disk', icon='FILEBROWSER')

    # register the blender substance classes
    classes = [
        PrincipledBDSFPreferences,
        Substance3DInBlender,
        ExternalPresetData,
        LoadedSbsars,
        SUBSTANCE_OT_CreateSbsar,
        SUBSTANCE_OT_DuplicateSbsar,
        SUBSTANCE_OT_ErrorBase,
        SUBSTANCE_OT_EngineError,
        SUBSTANCE_OT_SbsarNoOutputError,
        SUBSTANCE_OT_EngineTimeout,
        SUBSTANCE_OT_RemoveButton,
        SUBSTANCE_OT_RandomizeSeed,
        SUBSTANCE_OT_ToolsNotInstalled,
        SUBSTANCE_OT_UninstallTools,
        SUBSTANCE_OT_UpdateTools,
        SUBSTANCE_OT_GetTools,
        SUBSTANCE_OT_GotoShare,
        SUBSTANCE_OT_GotoSource,
        SUBSTANCE_OT_InstallTools,
        SUBSTANCE_OT_LoadSBSAR,
        SUBSTANCE_OT_LoadSBSPRS,
        SUBSTANCE_OT_NameSBSPRS,
        SUBSTANCE_OT_SaveSBSPRS,
        SUBSTANCE_OT_ExportSBSPRS,
        SUBSTANCE_ConfirmSBSPRSOverwrite,
        SUBSTANCE_ConfirmPresetOverwrite,
        SUBSTANCE_MT_ExtendedPresetOptions,
        SUBSTANCE_OT_ConfirmDelete,
        SUBSTANCE_OT_DeletePreset,
        SUBSTANCE_UL_SBSARDisplayList,
        SUBSTANCE_OT_SetDataPath,
        SUBSTANCE_OT_LoadFile,
        SUBSTANCE_OT_LoadPresetFile,
        SUBSTANCE_OT_ExportSBSPRSFile,
        SUBSTANCE_OT_RefreshSbsar,
    ]
    menuClassesForCleanup = []

    # Cache the previous data folder
    OLD_DATA_FOLDER = ''

    @persistent
    def save_pre_handler(scene):
        """ Save each sbsar parameter value as a preset """
        global OLD_DATA_FOLDER
        OLD_DATA_FOLDER = GetDataFolder()

        # save out current preset data
        for index, sbsar in enumerate(bpy.context.scene.loadedSbsars):
            SetDefaultAndCustomPreset(sbsar.blenderPresets,
                                      SbsarManager.getPresetValue(sbsar.id, 'Default'),
                                      SbsarManager.getPresetValue(sbsar.id, 'Custom'))
    bpy.app.handlers.save_pre.append(save_pre_handler)

    @persistent
    def save_post_handler(scene):
        """ When saved copy over any temporary textures """
        global OLD_DATA_FOLDER
        texPath = GetDataFolder()
        tmpFolder = GetTempDataFolder()

        # if the old data folder is the temp dir then safely delete its contents
        if CopyDataFolder(OLD_DATA_FOLDER, texPath, OLD_DATA_FOLDER == tmpFolder):
            RefreshLoadedSBSARData()
    bpy.app.handlers.save_post.append(save_post_handler)

    @persistent
    def load_post_handler(scene):
        """ Reload SBSARs and update the id from the tools """
        if len(bpy.data.filepath) < 1:
            # New blend file
            SbsarManager.clearData()
            bpy.context.scene.loadedSbsars.clear()
        else:
            # Loaded a blend file
            RefreshLoadedSBSARData()

        # re-register a function guarenteed to run on the main thread
        bpy.app.timers.register(ExecuteQueuedFunction)
    bpy.app.handlers.load_post.append(load_post_handler)

    def RefreshLoadedSBSARData():
        """ Refresh all the loaded SBSAR data -- usually because the textures have moved """
        if not AreToolsInstalled():
            bpy.ops.substance.tools_not_installed('INVOKE_DEFAULT')

        # Load the data
        PushCursor('WAIT')
        global ReloadingSBSARs
        ReloadingSBSARs = True
        sbsarsLoaded = []

        # establish connection if needed
        if not SbsarManager.sbsarClient.servers_running:
            SbsarManager.connect()

        # repopulate the data
        haveSbsars = len(bpy.context.scene.loadedSbsars) > 0
        if haveSbsars:
            for index, sbsar in enumerate(bpy.context.scene.loadedSbsars):

                # load the sbsar data
                loadPreset = False
                created = SbsarManager.createSbsarData(sbsar.id, sbsar.presetName, sbsar.blenderPresets, sbsar.filepath)
                if created != 'SUCCESS':
                    loadPreset = True
                    sbsar.id = SbsarManager.loadSbsar(sbsar.filepath, bpy.context, True, sbsar.presetName, '')

                SbsarManager.initializePresets(SbsarManager.sbsars[sbsar.id], sbsar.blenderPresets,
                                               '', sbsar.presetName)
                SbsarManager.sbsarParamMgr.buildGuiParameterGroups(SbsarManager.sbsarClient,
                                                                   SbsarManager.sbsars[sbsar.id])
                sbsarsLoaded.append(sbsar.id)
                data = SbsarManager.getSbsarDataFromId(sbsar.id)

                # relink the material nodes to the sbsar
                if data is not None:
                    for mat in bpy.data.materials:
                        if mat.node_tree is not None:
                            for node in mat.node_tree.nodes:
                                if node.name == sbsar.name + '_sbsar_group':
                                    LoadMaterialNodes(mat, data, node, sbsar.id)
                                    RebuildOutputLinkData(mat, data, node)

                # if the material had to be reloaded apply the preset
                if loadPreset:
                    SbsarManager.loadAndApplyPreset(data, sbsar.presetName, sbsar.id)

            # queue up the renders
            for loadedId in sbsarsLoaded:
                SbsarManager.renderSbsar(loadedId)
        else:
            SbsarManager.sbsarParamMgr.unregister()

        ReloadingSBSARs = False
        if haveSbsars:
            bpy.context.scene.sbsar_index = 0
        PopCursor()

    def LoadMaterialNodes(mat, data, node, newId):
        """ Refresh all data nodes """
        if data.mat is None:
            data.mat = mat
        if node.node_tree is not None:
            for subNode in node.node_tree.nodes:
                if subNode.type == 'TEX_IMAGE':
                    sbsar = SbsarManager.sbsars[newId]
                    texPath = data.getDataCacheTexName(data.name, subNode.label)
                    if subNode.image:
                        bpy.data.images.remove(subNode.image)
                    try:
                        subNode.image = bpy.data.images.load(texPath)
                    except Exception as e:
                        print('Failed to load image for: ' + str(newId) + ': ' + str(e))
                    sbsar.textureNodes.append(subNode)
                elif subNode.type == 'VALUE':
                    sbsar.valueNodes.append(subNode)

    def RebuildOutputLinkData(mat, data, groupNode):
        """ repopulate the output link data back to the sbsar data """
        bsdf = mat.node_tree.nodes['Principled BSDF']
        dispNode = None
        if bsdf:
            for node in mat.node_tree.nodes:
                if node.name == 'SBSARDispNode':
                    dispNode = node
            for output in groupNode.outputs:
                linkName = output.name
                if dispNode and output.name == 'Height':
                    toNode = dispNode.inputs['Height']
                    linkName = 'Displacement'
                else:
                    toNode = bsdf.inputs[output.name]
                oLink = SbsarOutputLink(toNode, output)
                link = doesLinkExist(mat, toNode, output)
                if link:
                    oLink.enabled = True
                    oLink.link = link
                data.outputLinks[linkName] = oLink

    def doesLinkExist(mat, to, fr):
        """ Return true if the link between the two nodes exists """
        for link in mat.node_tree.links:
            if link.to_socket == to and link.from_socket == fr:
                return link
        return False

    def sbsar_list_update(self, context):
        """ Notify the edit parameter window to update the displayed parameters """
        global ReloadingSBSARs

        # skip any panel updates until after all sbsars were loaded
        if not ReloadingSBSARs:
            sbsar = context.scene.loadedSbsars[context.scene.sbsar_index]
            sbsarData = SbsarManager.getSbsarDataFromId(sbsar.id)
            if sbsarData is not None:
                SbsarManager.sbsarParamMgr.populatePanels(context, sbsarData, sbsarData.guiParameters,
                                                          SbsarManager.spaces, sbsar.presetName, RunUIUpdateOutput)

    def register():
        """ register all blender addon classes and shortcuts """
        print('Initializing Substance 3D in Blender')

        # Start the Substance 3D Integration Tools
        if AreToolsInstalled():
            StartTools()

        # add the panel to multiple spaces
        for space in SbsarManager.spaces:
            classes.append(SubstancePanelFactory(space[1]))
            menuClass = SubstanceMenuFactory(space[1])
            classes.append(menuClass)
            menuClassesForCleanup.append(menuClass)

            # add the kaymappings for each space
            km = Substance3DInBlender.keymap
            kbModifiers = [True, True, False]
            km.addKeymap('U', menuClass.bl_idname, 'Substance 3D Menu', False, kbModifiers, space)
            km.addKeymap('L', SUBSTANCE_OT_LoadSBSAR.bl_idname, 'Load Substance 3D material', True, kbModifiers, space)
            km.addKeymap('M', SUBSTANCE_OT_CreateSbsar.bl_idname, 'Attach Substance 3D material',
                         True, kbModifiers, space)

        # register all of the classes
        for cls in classes:
            bpy.utils.register_class(cls)

        # sbsar list
        scene = bpy.types.Scene
        scene.loadedSbsars = CollectionProperty(type=LoadedSbsars)
        scene.sbsar_index = IntProperty(name='SBSAR Index', default=0,
                                        options={'HIDDEN'}, update=sbsar_list_update)

        # Setup shader
        addon = bpy.context.preferences.addons['Substance3DInBlender']
        SbsarManager.sbsarRenderCallback.preferences = addon.preferences

    def unregister():
        """ unregister all blender addon classes and shortcuts """
        print('Shutting down Substance in Blender')

        # cleanup scene data
        for scene in bpy.data.scenes:
            scene.loadedSbsars.clear()
        SbsarManager.shutdown()
        del bpy.types.Scene.loadedSbsars

        # cleanup keymappings
        Substance3DInBlender.keymap.unregister()

        # cleanup classes
        for cls in classes:
            bpy.utils.unregister_class(cls)

        # Stop the Remote Engine
        StopTools()

        # remove handlers
        bpy.app.handlers.save_pre.remove(save_pre_handler)
        bpy.app.handlers.save_post.remove(save_post_handler)
        bpy.app.handlers.load_post.remove(load_post_handler)

    if __name__ == '__main__':
        register()
except Exception:
    pass
