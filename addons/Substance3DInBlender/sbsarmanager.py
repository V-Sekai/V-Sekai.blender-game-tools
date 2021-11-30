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


# Substance SBSAR Manager
# 9/08/2020
import bpy
import json
import re
from .mainthread import PopCursor, PushCursor, RunOnMainThread
from .network.sbsarioclient import SbsarClient, SbsarRenderCallbackHandler, SbsarRenderCallbackInterface
from .sbsardata import PathLeaf, SbsarData
from .ui.nodegraph import CreateMaterial
from .ui.parammanager import GetParamName, SbsarParamMgr


def GetArea(areas, name):
    """ Test if an area is on screen """
    for area in areas:
        if area.type == name:
            return area
    return None


def GetUniqueName(context, name):
    """ Fixup any sbsar naming collision """
    foundName = False
    nameCount = 1
    lastChar = ''
    for sb in context.scene.loadedSbsars:
        if sb.name.startswith(name):
            foundName = True

            # find the highest value suffix on the name
            lastChar = re.findall('^.*_([0-9]+)$', sb.name)
            if len(lastChar) > 0:
                if lastChar[0].isnumeric:
                    currentCount = int(lastChar[0]) + 1
                    if currentCount > nameCount:
                        nameCount = currentCount

    # append the new suffix
    if foundName:
        name = name + '_' + str(nameCount)
    return name


def UIOutputUpdated(self, context, param, sbsarData):
    """ Output Has Update """
    name = GetParamName(param)
    value = getattr(self, name, True)

    # update custom preset values when not applying the default
    if sbsarData.applyingCustomPreset:
        sbsarData.customOutputPresetValues[name] = value

        # update disabled custom output
        sbsar = context.scene.loadedSbsars[context.scene.sbsar_index]
        if value:
            if name in sbsar.customDisabledOutputs:
                sbsar.customDisabledOutputs = sbsar.customDisabledOutputs.replace(name, '')
        else:
            if name not in sbsar.customDisabledOutputs:
                sbsar.customDisabledOutputs += (',' + name)
        sbsar.customDisabledOutputs = sbsar.customDisabledOutputs.replace(',,', ',')

    # update the link
    if sbsarData.mat:
        try:
            oLink = sbsarData.outputLinks[name]
            if value:
                oLink.addLink(sbsarData.mat.node_tree.links)
            else:
                oLink.removeLink(sbsarData.mat.node_tree.links)
            sbsarData.mat.update_tag()
        except Exception:
            print('Failed to modify link for: ' + name)


def RunUIUpdateOutput(param, sbsarData):
    """ Run the proper output update function """
    return lambda a, b: UIOutputUpdated(a, b, param, sbsarData)


def GetDefaultAndCustomPreset(presets):
    """ Get the default and custom preset values from the saved property group"""
    defaultPreset = ''
    customPreset = ''
    if presets:
        for p in presets:
            if p.name == 'Default':
                defaultPreset = p.value
            if p.name == 'Custom':
                customPreset = p.value
    return defaultPreset, customPreset


def SetDefaultAndCustomPreset(presets, defaultValue, customValue):
    """ Set the default and custom preset values for the current property group"""
    setDefault = False
    setCustom = False
    if presets:
        for p in presets:
            if p.name == 'Default':
                p.value = defaultValue
            if p.name == 'Custom':
                p.value = customValue
    if not setDefault:
        AddPreset(presets, 'Default', defaultValue)
    if not setCustom:
        AddPreset(presets, 'Custom', customValue)


def AddPreset(presets, name, value):
    """ Add a preset to the blendfile presets list """
    p = presets.add()
    p.name = name
    p.value = value


def GetSavedPresetData(context, data):
    """ Return the list of saved presets for an SBSAR """
    sbsarIndex = bpy.context.scene.loadedSbsars.find(data.name)
    if sbsarIndex > -1:
        return context.scene.loadedSbsars[sbsarIndex].blenderPresets
    return None


class SbsarRenderCallback(SbsarRenderCallbackInterface):
    """ SBSAR Render callback interface """

    def updateRender(self, data):
        """ Callback function when the remote engine finishs a render """
        jsonData = json.loads(data)
        RunOnMainThread(lambda: SbsarManager.runUpdateData(jsonData))
        SbsarManager.sbsars[jsonData['id']].waitOnEvent()
        RunOnMainThread(lambda: SbsarManager.submitQueuedRender())


class SbsarRenderListener():
    """ Register a function to get notified when a render is complete """
    @classmethod
    def onRenderComplete(cls, sbsarId):
        pass


class SbsarManager():
    """ Manage the SBSAR data """

    # Dictionary of SBSAR data
    sbsars = {}

    # The Tools SBSARIO callback
    sbsarClient = SbsarClient()

    # The Tools render callback
    sbsarRenderCallback = SbsarRenderCallback()

    # Display and modify parameters
    sbsarParamMgr = SbsarParamMgr()

    # Areas that must be redrawn after update
    cachedAreas = {}

    # A list of SBSAR Ids that need to be rendered
    renderList = []

    # A list of notify functions when a render is complete
    renderListeners = []

    # list the spaces to access the substance menu
    spaces = [['3D View', 'VIEW_3D'],
              ['Node Editor', 'NODE_EDITOR'],
              ['Image Generic', 'IMAGE_EDITOR']]

    @classmethod
    def connect(cls):
        """ Connect to the remote engine and register the callback """
        cls.sbsarClient.connect(SbsarRenderCallbackHandler)
        SbsarRenderCallbackHandler.addListener(cls.sbsarRenderCallback)
        cls.sbsarParamMgr.setup(cls.sbsarClient)

    @classmethod
    def shutdown(cls):
        """ Shutdown and Stop all servers """
        cls.clearData()
        cls.sbsarClient.stopServers()
        SbsarRenderCallbackHandler.removeListener(cls.sbsarRenderCallback)

    @classmethod
    def clearData(cls):
        """ Clear stored data """
        for sbsar in cls.sbsars:
            cls.sbsars[sbsar].cleanup()
        cls.sbsars = {}
        cls.sbsarParamMgr.unregister()

    @classmethod
    def cleanupSbsarData(cls, sbsarId):
        """ Clear specific sbsar data """
        sbsarData = cls.getSbsarDataFromId(sbsarId)
        if sbsarData:
            sbsarData.cleanup()
            if sbsarId == cls.getActiveSbsarId():
                cls.sbsarParamMgr.unregister()

    @classmethod
    def runUpdateData(cls, data):
        """ Called when it is safe to update material data """
        if data is not None:
            sbsarId = data['id']
            cls.updateActiveRenderedOutputs(sbsarId, data)
            sbsarData = cls.sbsars[sbsarId]
            sbsarData.renderDataEvent.set()

            # store the custom preset
            if sbsarData.applyingCustomPreset:
                response = SbsarManager.sbsarClient.savePreset(sbsarId)
                if response is not None:
                    rjson = response.json()
                    sbsarData.presets['Custom'] = str(rjson['presets'])
                else:
                    print('Unable to save custom preset')
            else:
                sbsarData.applyingCustomPreset = True

            # notify any listeners
            for listener in cls.renderListeners:
                listener.onRenderComplete(sbsarId)

            # restore the cursor
            PopCursor()

    @classmethod
    def submitQueuedRender(cls):
        """ Check if more ids have been queued up to be rendered """
        if len(cls.renderList) > 0:
            sbid = cls.renderList.pop(0)
            cls.sbsarClient.render(sbid)
        else:
            cls.sbsarClient.setRenderQueued(False)

    @classmethod
    def getActiveSbsarId(cls):
        """ Get the active SBSAR Id """
        return cls.sbsarParamMgr.sbsarId

    @classmethod
    def setActiveSbsarId(cls, newValue):
        """ Set the active SBSAR Id """
        SbsarParamMgr.sbsarId = newValue

    @classmethod
    def renderActiveSbsar(cls):
        """ Send render request to the remote engine for the active sbsar """
        cls.renderSbsar(cls.getActiveSbsarId())

    @classmethod
    def renderSbsar(cls, sbsarId):
        """ Submit a render request to the remote engine for an sbsar """
        PushCursor('WAIT')
        if cls.sbsarClient.isRenderQueued():
            cls.renderList.append(sbsarId)
        else:
            cls.sbsarClient.render(sbsarId)

    @classmethod
    def getLoadedSbsarFromId(cls, id):
        """ Retrieve SBSAR data given the SBSAR ID """
        try:
            for i, sbsar in enumerate(bpy.context.scene.loadedSbsars):
                if sbsar.id == id:
                    return sbsar, i
        except Exception:
            pass
        return None, -1

    @classmethod
    def loadSbsar(cls, file, context, replaceLoadedSBSAR, presetName, duplciateId):
        """ Send a file to the remote engine for loading """

        # connect to the sbsar resource on the Tools
        duplicatedSbsar = len(duplciateId) > 0
        updateSbsarIndex = False
        if not cls.sbsarClient.servers_running:
            cls.connect()

        # send the sbsar file to the remote engine
        if duplicatedSbsar:
            sbsarid = cls.sbsarClient.duplicateSbsar(duplciateId)
            presets = GetSavedPresetData(context, cls.getSbsarDataFromId(duplciateId))
        else:
            sbsarid = cls.sbsarClient.sendFile(file)
            presets = None
        if sbsarid:
            if sbsarid.startswith('ERROR'):
                return cls.loadFailed('Send File Failed: ' + str(sbsarid), sbsarid)

            # create the internal data object
            cls.createSbsarData(sbsarid, presetName, presets, file)

            # check the SBSAR is compatible with the plugin
            # if no output was found report an error and remove it from the loaded list
            if not cls.sbsars[sbsarid].mapped_outputs:
                msg = 'No Compatible Outputs for Substance 3D material: ' + str(sbsarid)
                cls.sbsars.pop(sbsarid)
                return cls.loadFailed(msg, 'ERROR incompatible output')

            # setup preset data
            cls.initializePresets(cls.sbsars[sbsarid], presets, duplciateId, presetName)

            # build the UI panels
            cls.sbsarParamMgr.buildGuiParameterGroups(cls.sbsarClient, cls.sbsars[sbsarid])

            if cls.sbsars[sbsarid].outList is not None:
                addon = context.preferences.addons['Substance3DInBlender']
                cls.sbsarRenderCallback.preferences = addon.preferences

                # check for name collisions
                if not replaceLoadedSBSAR:
                    cls.sbsars[sbsarid].name = GetUniqueName(context, cls.sbsars[sbsarid].name)

                # create the sbsar entry and attach it to the scene
                sbsarIndex = bpy.context.scene.loadedSbsars.find(cls.sbsars[sbsarid].name)
                if sbsarIndex < 0:
                    sbsar = context.scene.loadedSbsars.add()
                    SetDefaultAndCustomPreset(sbsar.blenderPresets,
                                              cls.getPresetValue(sbsarid, 'Default'),
                                              cls.getPresetValue(sbsarid, 'Custom'))
                else:
                    sbsar = context.scene.loadedSbsars[sbsarIndex]
                sbsar.name = cls.sbsars[sbsarid].name
                sbsar.id = sbsarid
                sbsar.filepath = file
                sbsar.presetName = presetName

                # update the UI list to point to the latest sbsar
                updateSbsarIndex = True
            else:
                print(file + ': Has no outputs to render')
            cls.cachedAreas = bpy.context.window.screen.areas
        else:
            return cls.loadFailed('Send File returned no ID', 'ERROR')

        if updateSbsarIndex:
            context.scene.sbsar_index = len(context.scene.loadedSbsars) - 1
        return sbsarid

    @classmethod
    def refreshCurrentSbsar(cls, context):
        """ Reload the current sbsar from disk """
        sbsarData = cls.getActiveSbsarData()

        # reload the sbsar
        newId = cls.sbsarClient.sendFile(sbsarData.file)
        if newId:
            if not newId.startswith('ERROR'):

                # remove the old
                cls.sbsarClient.deleteSbsar(sbsarData.id)

                # re-key the data to the new id
                cls.sbsars[newId] = cls.sbsars.pop(sbsarData.id)
                cls.sbsars[newId].id = newId

                # update the saved data
                sbsarIndex = bpy.context.scene.loadedSbsars.find(sbsarData.name)
                savedData = context.scene.loadedSbsars[sbsarIndex]
                savedData.id = str(newId)

                # load the old preset and update the parameters
                cls.loadAndApplyPreset(sbsarData, savedData.presetName, newId)
                return str(newId)
        print('Failed to refresh: ' + sbsarData.file)
        return ''

    @classmethod
    def loadAndApplyPreset(cls, data, presetName, sbsarId):
        """ Load the preset and update the parameter values """
        cls.sbsarParamMgr.loadPreset(data.presets[presetName], sbsarId)
        retCode, paramList = cls.sbsarClient.getAllParams(sbsarId)
        if retCode != 'SUCCESS':
            return cls.loadFailed('No parameters refreshed for Substance 3D material: ' + str(sbsarId), retCode)
        else:
            cls.sbsars[sbsarId].parameters = paramList

        # build the Parameter window for the new sbsar and render
        cls.sbsarParamMgr.buildGuiParameterGroups(cls.sbsarClient, data)

    @classmethod
    def createSbsarData(cls, sbsarid, presetName, presets, file):
        """ Create the blender sbsar data object """

        # if the normal_output is directX switch to OpenGL
        retCode, paramList = cls.sbsarClient.getAllParams(sbsarid)
        if retCode != 'SUCCESS':
            return cls.loadFailed('No parameters for Substance 3D material: ' + str(sbsarid), retCode)

        # if using the default preset ensure openGL
        if presetName == 'Default':
            cls.sbsarParamMgr.ensureOpenGL(paramList, sbsarid)

        # reload the parameters after the preset and openGL checks
        retCode, paramList = cls.sbsarClient.getAllParams(sbsarid)
        if retCode != 'SUCCESS':
            msg = 'No parameters for Substance 3D material: ' + str(sbsarid)
            return cls.loadFailed(msg, retCode)

        # get the output list
        retCode, outList = cls.sbsarClient.queryAllOutputs(sbsarid)
        if retCode != 'SUCCESS':
            msg = 'No Outputs for Substance 3D material: ' + str(sbsarid)
            return cls.loadFailed(msg, retCode)

        # populate sbsar data
        name = PathLeaf(file)
        name = name.replace('.sbsar', '')
        mapping = cls.sbsarRenderCallback.preferences.principled_mapping
        cls.sbsars[sbsarid] = SbsarData(name, file, sbsarid, paramList, outList, mapping, presets)
        return 'SUCCESS'

    @classmethod
    def initializePresets(cls, data, presets, duplciateId, currentName):
        """ Initialize internal preset data """
        if len(currentName) < 1:
            currentName = 'Default'

        # get special preset values
        defaultPreset, customPreset = GetDefaultAndCustomPreset(presets)
        data.presets['Custom'] = customPreset
        data.presets['Default'] = defaultPreset

        # save the initial parameters
        response = SbsarManager.sbsarClient.savePreset(data.id)
        if response is not None and currentName in data.presets and len(data.presets[currentName]) < 1:
            rjson = response.json()
            data.presets[currentName] = str(rjson['presets'])
        else:
            print('Unable to save default preset')

        # add embedded presets to the list
        retCode, emPresets = cls.sbsarClient.getEmbeddedPresets(data.id)
        if retCode == 'SUCCESS':
            if emPresets:
                for emPreset in emPresets:
                    data.presets[emPreset['label']] = str(emPreset)

    @classmethod
    def loadFailed(cls, msg, retCode):
        """ Print the error message and return the proper code """
        print(msg)
        cls.setActiveSbsarId('')
        return retCode

    @classmethod
    def updateActiveRandomSeed(cls, value):
        """ Update the random seed for the active sbsar """
        sbsarData = cls.getActiveSbsarData()
        if sbsarData:
            graphClassName = cls.sbsarParamMgr.getPropClassName('Graph Parameters', cls.sbsarParamMgr.propertySuffix,
                                                                sbsarData.id[-4:])
            cls.sbsarParamMgr.setProperty(graphClassName, '$randomseed', value)
        else:
            print('No Sbsar data to randomize the seed')

    @classmethod
    def updateActiveRenderedOutputs(cls, sbsarid, renderData):
        """ Update the output data for the SBSAR with the given ID """
        if sbsarid in cls.sbsars.keys():
            prefs = cls.sbsarRenderCallback.preferences
            mapping = prefs.principled_mapping
            cls.sbsars[sbsarid].updateRenderedOutputs(renderData, mapping)

            # check if the material should be automatically attached
            if cls.sbsars[sbsarid].autoCreateMat:
                cls.sbsars[sbsarid].autoCreateMat = False
                try:
                    bpy.ops.substance.create_material(sbsar_id=sbsarid)
                except Exception:
                    pass
        else:
            print('Invalid Update Render Ouputs ID: ' + str(sbsarid))

    @classmethod
    def createMaterial(cls, context, texture_mapping, obj, sbsarData):
        """ Create a blender material from the active sbsar id
            And attach these material to the selected objects """
        return CreateMaterial(cls.sbsarParamMgr, sbsarData, context, texture_mapping, obj)

    @classmethod
    def removeActiveSbsar(cls):
        """ Remove the active sbsar from the list """
        sbsar, index = cls.getLoadedSbsarFromId(cls.getActiveSbsarId())
        numLoaded = len(bpy.context.scene.loadedSbsars)
        if index > -1:
            sbsarData = cls.getSbsarDataFromId(sbsar.id)
            sbsarData.cleanup()
            bpy.context.scene.loadedSbsars.remove(index)
            cls.sbsars.pop(id, None)
            if numLoaded > 1:
                if index == 0:
                    bpy.context.scene.sbsar_index = 0
                else:
                    bpy.context.scene.sbsar_index = index-1
            else:
                cls.sbsarParamMgr.unregister()

    @classmethod
    def getActiveSbsarData(cls):
        """ Return the SBSAR data for the current active sbsar ID """
        sbsarId = cls.getActiveSbsarId()
        return cls.getSbsarDataFromId(sbsarId)

    @classmethod
    def getSbsarDataFromId(cls, sbsarId):
        """ Return the SBSAR data for the current active sbsar ID """
        if sbsarId in cls.sbsars.keys():
            return cls.sbsars[sbsarId]
        else:
            return None

    @classmethod
    def getPresetValue(cls, sbsarId, name):
        """ Return the custom preset value for the sbsar """
        sbsarData = cls.getSbsarDataFromId(sbsarId)
        if name in sbsarData.presets:
            return sbsarData.presets[name]
        return ''

    @classmethod
    def allowPresetChange(cls, allow):
        """ Enable disable preset parameter updates"""
        SbsarParamMgr.allowPresetChange(allow)

    @classmethod
    def addRenderListener(cls, listener):
        """ Add a listener when sbsars finish rendering """
        cls.renderListeners.append(listener)

    @classmethod
    def removeRenderListener(cls, listener):
        """ Remove a listener from render notifications """
        cls.renderListeners.remove(listener)
