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


# Substance SBSAR Data
# 9/08/2020
import bpy
import ntpath
import os
import shutil
import sys
import threading
from datetime import datetime
from distutils.dir_util import copy_tree, remove_tree
from pathlib import Path
from .ui.nodegraph import GetPropertyClassKeywordAttribute, SetTexNodeColorSpace
from .ui.parammanager import OUTPUT_GROUP_NAME, GetParamName

WAIT_EVENT_DEFAULT_TIMEOUT = 60

# unique folder for this sessions temporary assets
gSessionFolder = datetime.now().strftime("%d%m%Y_%H%M%S")


def GetTempDataFolder():
    """ Get the temporary data folder """
    prefTmpDir = bpy.context.preferences.filepaths.temporary_directory
    if not sys.platform.startswith('win') and len(prefTmpDir) < 2:
        prefTmpDir = str(Path.home())
    return os.path.abspath(prefTmpDir + "/Substance3DInBlenderData/" + gSessionFolder)


def GetDataFolder():
    """ Return the current folder to store this projects texture data """
    blendFilePath = bpy.context.blend_data.filepath
    blendFilePath = blendFilePath.rsplit('.', 1)[0]
    prefs = bpy.context.preferences
    dataPath = prefs.addons['Substance3DInBlender'].preferences.data_path
    if len(blendFilePath) < 2:
        texPath = GetTempDataFolder()
    else:
        if len(dataPath) > 0:
            dataPath = dataPath + "/"
        texPath = blendFilePath + "/" + dataPath + "Substance3DInBlenderData"
    texPath = bpy.path.native_pathsep(texPath)
    return texPath


def CopyDataFolder(src, dst, removeSrc):
    """ Return True if there were temporary files copied to the destination """
    if os.path.exists(src):
        if src != dst:
            src_dir = os.listdir(src)
            if len(src_dir) > 0:
                copy_tree(src, dst)
                if removeSrc:
                    remove_tree(src)
                return True
    return False


def PathLeaf(path):
    """ Return the file name from a full path """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def RemoveFile(file):
    """ Remove a file if it exists on """
    try:
        if os.path.exists(file):
            os.remove(file)
    except Exception as e:
        print('Failed to delete: ' + file)
        print(e)


class SbsarData():
    """ The stored data from a loaded SBSAR """
    def __init__(self, name, file, id, params, outList, mapping, presets):

        # SBSAR Name
        self.name = name

        # SBSAR File
        self.file = file

        # ID from the tools
        self.id = id

        # Parameters for the SBSAR
        self.parameters = params

        # Dictionary of properly grouped parameters
        self.guiParameters = {}

        # Dictionary of embedded presets
        self.presets = {}

        # List of presets that were added (these can be deleted)
        self.addedPresetNames = []

        # Is the current render using the default preset
        self.applyingCustomPreset = False

        # Custom preset values for the outputs
        self.customOutputPresetValues = {}

        # List of all the sbsar outputs
        self.outList = outList

        # Dictionary of outputs and their channel use
        self.usageOutputs = {}

        # Dictionary of all the mapped outputs to the current shader
        self.mapped_outputs = {}

        # List of all the texture nodes
        self.textureNodes = []

        # List of all the value nodes
        self.valueNodes = []

        # The Material generated from this SBSAR
        self.mat = None

        # Store the ouptut links in order to quickly enable/disable
        self.outputLinks = {}

        # After render should the material automatically be created
        self.autoCreateMat = False

        # Network requests wait for the data to be consumed
        self.renderDataEvent = threading.Event()

        # populate the usage output dictionary
        self.populateUsageOutputs(self.outList)

        # populate the mapped outputs
        self.mapOutputs(self.outList, mapping)

        # load the presets
        if presets:
            for p in presets:
                self.presets[p.name] = p.value
                self.addedPresetNames.append(p.name)

    def cleanup(self):
        """ Cleanup the registered classes """
        self.mat = None

    def waitOnEvent(self, timeout=WAIT_EVENT_DEFAULT_TIMEOUT):
        """ Clear the event and wait for it to get set again """
        self.renderDataEvent.clear()
        self.renderDataEvent.wait(timeout)

    def createSBSARTextureFolder(self, name):
        """ Create a folder to cache textures """
        texPath = GetDataFolder() + "/" + name + "/"
        texPath = bpy.path.native_pathsep(texPath)
        if not os.path.exists(texPath):
            os.makedirs(texPath, mode=0o777)

    def getDataCacheTexName(self, name, label):
        """ Get the cached texture name """
        texPath = GetDataFolder() + "/" + name + "/" + label + '.tga'
        texPath = bpy.path.native_pathsep(texPath)
        return texPath

    def updateRenderedOutputs(self, rendered_outputs, mapping):
        """ Update the Shader texture with the new renders """
        if self.outList is None:
            print('No outputs to update: ' + self.name)
            return

        # Update each of the texture maps
        outputs = rendered_outputs['outputs']
        self.mapOutputs(outputs, mapping)

    def populateUsageOutputs(self, outputs):
        """ Create a dictionary of outputs and their usages """
        for output in outputs:
            channelUse = output['defaultChannelUse']
            if channelUse not in self.usageOutputs:
                self.usageOutputs[channelUse] = output

    def mapOutputs(self, outputs, mapping):
        """ Setup the mapping from outputs to blender inputs """

        # create map of output id and outputs
        outputIdMap = {}
        for output in outputs:
            outputIdMap[output['id']] = output

        for blenderName in mapping.__annotations__.keys():

            # get a list of all appropriate sbsar texture values
            propValue = getattr(mapping, blenderName)
            if isinstance(propValue, str):
                propName = GetPropertyClassKeywordAttribute(mapping.__annotations__[blenderName], 'name')
                allowedNames = propValue.split(',')
                allowedNames = list([s.strip() for s in allowedNames])

                # Find matching texture
                fallbackId = None
                if blenderName in self.usageOutputs:
                    fallbackId = self.usageOutputs[blenderName]['id']
                output = self.foundMatchingTexture(allowedNames, fallbackId, outputIdMap)
                if output:
                    self.updateTexture(output, output['id'], propName)

    def foundMatchingTexture(self, allowedNames, fallbackId, outputIdMap):
        """ Find which blender texture to replace """
        retOutput = None
        for outFromList in self.outList:
            if outFromList['identifier'] in allowedNames:
                targetId = outFromList['id']
                if targetId in outputIdMap:
                    return outputIdMap[targetId]

            # if no texture matches the allowed names match the first acceptable defaultUsage output
            elif fallbackId in outputIdMap:
                retOutput = outputIdMap[fallbackId]
        return retOutput

    def updateTexture(self, output, targetId, propName):
        """ Map updated texture """
        outputPath = ''
        outputValue = None
        updatePath = False
        if 'path' in output:
            outputPath = output['path']
            updatePath = True
        if 'value' in output:
            outputValue = output['value']

        # Move the new texture into the proper location
        if updatePath:
            self.createSBSARTextureFolder(self.name)
            cacheName = self.getDataCacheTexName(self.name, propName)
            try:
                shutil.move(outputPath, cacheName)
            except Exception as e:
                print('Failed to copy new texture src: ' + outputPath + ' dst: ' + cacheName)
                print(e)
            outputPath = cacheName
            output['path'] = cacheName

            # If the node already exists replace the data
            if propName in self.mapped_outputs:
                self.replaceNode(targetId, outputValue)

        # update the mapped output
        self.mapped_outputs[propName] = (outputPath, outputValue, targetId)

    def replaceNode(self, propertyID, newValue):
        """ Loop through texture and value nodes and updating their data """
        strPropertyID = str(propertyID)
        for texNode in self.textureNodes:
            if texNode.name.endswith(strPropertyID):
                texNode.image.reload()
                SetTexNodeColorSpace(texNode)
        for valNode in self.valueNodes:
            if valNode.name.endswith(strPropertyID):
                if newValue is None:
                    print('Cannot update None Value for property: ' + strPropertyID)
                else:
                    valNode.outputs[0].default_value = newValue

    def populateGuiParameters(self):
        """ Populate the GUI Parameters generated from the SBSAR parameters """
        self.guiParameters = {}

        # panel order is dependent on registration order
        addedGraphParams = False
        addedOutputParams = False

        for param in self.parameters:
            if addedGraphParams and not addedOutputParams:
                # Once the Graph Parameter panel is added add output Channels to make sure
                # they are positioned above the rest of the parameter panels
                addedOutputParams = True
                self.addOutputChannels()

            groupName = param['guiGroup']
            label = GetParamName(param)
            if label == '$outputsize':
                # add output size as a graph parameter
                self.addGuiParamToGroup('Graph Parameters', param)
                addedGraphParams = True
            elif label == '$randomseed':
                # add randomseed as the last graph parameter and setup Presets to follow
                self.addGuiParamToGroup('Graph Parameters', param)
                self.addPresetParam()
                addedGraphParams = True
            elif len(groupName) > 0:
                self.addGuiParamToGroup(groupName, param)
            else:
                self.addGuiParamToGroup('Parameters', param)

    def addGuiParamToGroup(self, groupName, param):
        """ Create the param group if needed then add the param to it """
        if groupName in self.guiParameters:
            currentList = self.guiParameters[groupName]
            currentList.append(dict(param))
        else:
            self.guiParameters[groupName] = [dict(param)]

    def addOutputToGuiGroup(self, output):
        """ Add the supported output to the GUI Outputs list """
        if OUTPUT_GROUP_NAME in self.guiParameters:
            currentList = self.guiParameters[OUTPUT_GROUP_NAME]
            currentList.append(output)
        else:
            self.guiParameters[OUTPUT_GROUP_NAME] = [output]

    def addOutputChannels(self):
        """ Create the output channel property group """
        for output in self.mapped_outputs:
            self.addOutputToGuiGroup(output)

            # if this output is being added for the first time default to True
            if output not in self.customOutputPresetValues:
                self.customOutputPresetValues[output] = True

    def addPresetParam(self):
        """ Create a preset parameter for the UI to populate """
        presetParam = {'label': 'Preset'}
        self.addGuiParamToGroup('Graph Parameters', presetParam)

    def removePreset(self, presetName):
        """ Remove the current preset """
        self.addedPresetNames.remove(presetName)
        self.presets.pop(presetName)
