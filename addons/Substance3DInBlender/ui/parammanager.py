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


# Substance Parameters
# 03/01/2021

import ast
import bpy
import re
import sys
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty,
                       IntProperty, IntVectorProperty, PointerProperty, StringProperty)
from bpy.types import Menu, PropertyGroup
from mathutils import Vector

OUTPUT_GROUP_NAME = 'Outputs'
CHANNEL_GROUP_NAME = 'Channels'
PROP_ID_NAME_SEPARATOR = '._'
SLIDER_SUFFIX = '_slider_'
MAX_BLENDER_PROPERTY_NAME_LENGTH = 63

supported_resolutions = [('5', '32', ''),
                         ('6', '64', ''),
                         ('7', '128', ''),
                         ('8', '256', ''),
                         ('9', '512', ''),
                         ('10', '1024', ''),
                         ('11', '2048', ''),
                         ('12', '4096', '')]


def GetParamName(param):
    """ Generate the proper parameter Name """
    if 'label' in param:
        name = param['label']
    elif 'identifier' in param:
        name = param['identifier']
    elif isinstance(param, str):
        name = param
    else:
        print('Undefined name for: ' + str(param))
        name = 'not defined'

    # check if its a slider
    if isParameterASlider(param, name):
        name += SLIDER_SUFFIX

    # randomseed and outputsize are unique per sbsar and do not need the unique param identifier
    if name != '$randomseed' and name != '$outputsize':
        if 'id' in param:
            name = str(param['id']) + PROP_ID_NAME_SEPARATOR + name

    if len(name) > MAX_BLENDER_PROPERTY_NAME_LENGTH:
        name = ShortenName(name)
    return name


def ShortenName(name):
    """ Blender has a maximum property name length """
    currentLength = len(name)
    numberofCharactersToStrip = currentLength - MAX_BLENDER_PROPERTY_NAME_LENGTH
    if numberofCharactersToStrip > 0:
        if name.endswith(SLIDER_SUFFIX):
            numberofCharactersToStrip += len(SLIDER_SUFFIX)
            shortenedName = name[:-numberofCharactersToStrip]
            shortenedName = shortenedName + SLIDER_SUFFIX
        else:
            shortenedName = name[:-numberofCharactersToStrip]
        return shortenedName
    else:
        return name


def isParameterASlider(param, name):
    """ If the paramter is of type slider or has a max value use a slider """
    isSlider = False
    if name != '$outputsize' and name != '$randomseed':
        try:
            attType = param['guiWidget']
            if attType == 'Slider':
                isSlider = True
        except Exception:
            pass
        if not isSlider:
            try:
                if param['maxValue'][0] > 0:
                    isSlider = True
            except Exception:
                try:
                    if param['maxValue'] > 0:
                        isSlider = True
                except Exception:
                    pass
    return isSlider


def IsEnum(type):
    """ Check if a param type translates to an enum property """
    return type == 'Combobox'


def IsVector(paramType):
    """ Check if a param type translates to a vector of values """
    pType = paramType.lower()
    if pType == 'integer' or pType == 'float':
        return False
    elif pType == 'color' or pType.startswith('float'):
        return True
    return False


def IsVisible(param):
    """ Check the visible if status of a parameter """
    if 'visibleIf' in param:
        return param['visibleIf']
    else:
        return True


def GetPropertyGroupsFromId(sbsarId):
    """ Get the UI property group for the given sbsarid """
    propGroups = []
    for attr, value in bpy.context.scene.items():
        if attr.endswith(sbsarId[-4:]):
            propGroups.append(getattr(bpy.context.scene, attr, None))
    return propGroups


def GetUpdateResolutionValue(prop):
    """ Get the proper resolution values based on whether or not it is linked """
    islinked = getattr(prop, 'res_link')
    widthValue = int(getattr(prop, 'res_width'))
    if islinked:
        value = (widthValue, widthValue)
    else:
        heightValue = int(getattr(prop, 'res_height'))
        value = (widthValue, heightValue)
    return value


def ResolutionLinkUpdated(self, context, param):
    """ Send the resolution values to the remote engine """
    value = GetUpdateResolutionValue(self)
    SbsarParamMgr.updateParameter(self.sbsarId, param['id'], value, True, False)


def PresetUpdated(self, context, paramMgr, sbsarData):
    """ Send the resolution values to the remote engine """
    if SbsarParamMgr.enablePresetChange and not SbsarParamMgr.sbsarClient.isRenderQueued():
        presetName = getattr(self, 'Preset', None)
        if presetName:
            sbsar = context.scene.loadedSbsars[context.scene.sbsar_index]
            sbsar.presetName = presetName
            value = sbsarData.presets[presetName]

            # swap to openGL for embedded presets
            forceOpenGL = presetName not in sbsarData.addedPresetNames

            # if the user reset to default change the value after applying all parameter changes
            if presetName != 'Custom':
                # update any changes to the custom preset before swapping
                if sbsarData.applyingCustomPreset and 'Custom' in sbsar.blenderPresets:
                    sbsar.blenderPresets['Custom'].isResolutionLinked = paramMgr.getResolutionLinkValue(sbsarData)
                sbsarData.applyingCustomPreset = False

            # send the preset value to the remote engine
            sbsarId = self.sbsarId
            if SbsarParamMgr:
                SbsarParamMgr.loadPreset(value, sbsarId)
                if forceOpenGL:
                    paramMgr.ensureOpenGL(sbsarData.parameters, sbsarId)
            else:
                print('No Parameter Manager -- unable to update preset')
            retCode, paramList = SbsarParamMgr.sbsarClient.getAllParams(sbsarId)
            if retCode == 'SUCCESS':
                sbsarData.parameters = paramList
                sbsarData.populateGuiParameters()

                # update the parameters
                paramMgr.updateProperties(sbsarData, presetName == 'Custom')

                # get saved resoution linked value
                presetData = GetPresetSaveData(sbsarData.name)
                if presetData:
                    linkVal = presetData.isResolutionLinked
                else:
                    linkVal = True
                SbsarParamMgr.setResolutionLinkValue(sbsarData, linkVal)

                # Trigger the parameter window to be rebuilt with the preset parameters
                context.scene.sbsar_index = context.scene.sbsar_index
            else:
                print('ParamManager PresetUpdated failed to get the parameters')


def ParameterUpdated(self, context, param, sbsarData):
    """ Parameter Has Update """
    name = GetParamName(param)
    if name == '$outputsize':
        value = GetUpdateResolutionValue(self)
    else:
        if 'enumValues' in param and len(param['enumValues']) > 0:
            value = int(getattr(self, name))
        else:
            value = getattr(self, name, None)
            if value is None:
                # the parameters values could have changed the suffix so check both cases
                if name.endswith(SLIDER_SUFFIX):
                    value = getattr(self, name[:-len(SLIDER_SUFFIX)], None)
                else:
                    value = getattr(self, name + SLIDER_SUFFIX, None)
    if value is not None:
        SbsarParamMgr.updateParameter(self.sbsarId, param['id'], value, True, sbsarData.applyingCustomPreset)
    else:
        print('No Value for: ' + name + ' to be updated')


def RunUpdate(param, sbsarData):
    """ Run the proper param update function """
    return lambda a, b: ParameterUpdated(a, b, param, sbsarData)


def RunResolutionLinkUpdate(param):
    """ Run the proper resolution link update function """
    return lambda a, b: ResolutionLinkUpdated(a, b, param)


def RunPresetUpdate(paramMgr, sbsarData):
    """ Run the preset update function """
    return lambda a, b: PresetUpdated(a, b, paramMgr, sbsarData)


def BuildPropertyGroupClass(className, paramMgr, sbsarData, params, isOutput, presetName, uiOutputCallback):
    """ Build the runtime property group """
    attributes = {}
    for param in params:
        attName = GetParamName(param)
        attributes['sbsarId'] = StringProperty(name='sbsarId', default=sbsarData.id)
        if attName == '$outputsize':
            SetupOutputSize(attributes, sbsarData, param)
        elif attName == '$randomseed':
            attributes[attName] = IntProperty(name='Random Seed', default=param['value'],
                                              max=param['maxValue'], min=param['minValue'],
                                              update=RunUpdate(param, sbsarData))
        elif attName == 'Preset':
            CreatePresetDropDown(paramMgr, attributes, sbsarData, attName, presetName)
        else:
            if isOutput:
                SetupOutputToggle(attributes, sbsarData, attName, param, uiOutputCallback)
            else:
                attType = param['guiWidget']
                if IsVisible(param) and len(attType) > 0:
                    if 'value' in param.keys():
                        if attType == 'Togglebutton':
                            SetupToggleButton(attributes, sbsarData, attName, param)
                        elif IsEnum(attType):
                            SetupEnum(attributes, sbsarData, attName, param)
                        elif attType == 'Slider':
                            SetupValueProperty(attributes, sbsarData, attName, param, 'NONE')
                        elif attType == 'Color':
                            SetupColor(attributes, sbsarData, attName, param)
                        elif attType == 'Angle':
                            SetupValueProperty(attributes, sbsarData, attName, param, 'ANGLE')
                        elif attType == 'Position':
                            if param['type'].startswith('float'):
                                SetupValueProperty(attributes, sbsarData, attName, param, 'XYZ')
                            else:
                                SetupValueProperty(attributes, sbsarData, attName, param)
                        else:
                            SetupValueProperty(attributes, sbsarData, attName, param)
                    else:
                        print(attName + ' of type: ' + param['type'] + ' currently not supported')

    # Build and Register the property group class
    if attributes:
        propertyGroupClass = type(className, (PropertyGroup,), {'__annotations__': attributes})
        return propertyGroupClass
    else:
        return None


def GetPresetSaveData(sbsarName):
    """ Get the currently selected saved preset data """
    sbsarIndex = bpy.context.scene.loadedSbsars.find(sbsarName)
    if sbsarIndex > -1:
        savedData = bpy.context.scene.loadedSbsars[sbsarIndex]
        if savedData.presetName in savedData.blenderPresets:
            return savedData.blenderPresets[savedData.presetName]
    return None


def SetupOutputSize(attributes, sbsarData, param):
    """ Setup a ToggleButton Attribute """
    defaultValues = param['value']
    defaultWidthIndex = max(0, defaultValues[0] - 5)
    defaultHeightIndex = max(0, defaultValues[1] - 5)
    defaultWidthValue = None
    defaultHeightValue = None

    # set the default values
    for i, val in enumerate(supported_resolutions):
        if i == defaultWidthIndex:
            defaultWidthValue = val[0]
        if i == defaultHeightIndex:
            defaultHeightValue = val[0]
        if defaultWidthValue is not None and defaultHeightValue is not None:
            break

    # create the attributes
    attributes['res_link'] = BoolProperty(name='Linked', default=True,
                                          update=RunResolutionLinkUpdate(param))
    attributes['res_width'] = EnumProperty(name='Width', default=defaultWidthValue, items=supported_resolutions,
                                           description='Supported resolution sizes',
                                           update=RunUpdate(param, sbsarData))
    attributes['res_height'] = EnumProperty(name='Height', default=defaultHeightValue, items=supported_resolutions,
                                            description='Supported resolution sizes',
                                            update=RunUpdate(param, sbsarData))


def CreatePresetDropDown(paramMgr, attributes, sbsarData, attName, presetName):
    """ Create the preset dropdown """
    if len(presetName) < 1:
        presetName = 'Default'
    presetItems = []
    for i, (key, value) in enumerate(sbsarData.presets.items()):
        presetItems.append((key, key, ''))
    if len(presetItems) > 0:
        attributes[attName] = EnumProperty(name='Presets', items=presetItems, default=presetName,
                                           update=RunPresetUpdate(paramMgr, sbsarData))


def SetupToggleButton(attributes, sbsarData, attName, param):
    """ Setup a ToggleButton Attribute """
    val = True
    if 'value' in param:
        val = param['value']
    if val:
        attributes[attName] = BoolProperty(name=attName, default=True, update=RunUpdate(param, sbsarData))
    else:
        attributes[attName] = BoolProperty(name=attName, default=False, update=RunUpdate(param, sbsarData))


def SetupOutputToggle(attributes, sbsarData, attName, param, uiOutputCallback):
    """ Setup a Toggle button with a specific update function for outputs """
    if attName in sbsarData.outputLinks:
        value = sbsarData.outputLinks[attName].enabled
    else:
        value = True
    attributes[attName] = BoolProperty(name=attName, default=value, update=uiOutputCallback(param, sbsarData))


def SetupValueProperty(attributes, sbsarData, attName, param, subtype='NONE'):
    """ Figure out which type of value property to create """
    name = GetParamName(param)
    try:
        vValue = Vector(param['value'])
        dimensions = len(vValue)
        maxValue = param['maxValue'][0]
        vecProperty = True
    except Exception:
        vecProperty = False
        maxValue = param['maxValue']

    # If there isn't a max value set it so blender doesnt lock to 0
    if maxValue <= 0:
        maxValue = sys.maxsize

    if vecProperty:
        CreateVectorProperty(attributes, sbsarData, attName, name, param, vValue, dimensions, maxValue, subtype)
    else:
        CreateProperty(attributes, sbsarData, attName, name, param, maxValue, subtype)


def CreateProperty(attributes, sbsarData, attName, name, param, maxValue, subtype):
    """ Create the property from the parameter """
    pType = param['type']
    if pType == 'integer':
        attributes[attName] = IntProperty(name=name, default=param['value'], max=maxValue,
                                          min=param['minValue'], subtype=subtype, update=RunUpdate(param, sbsarData))
    elif pType == 'float':
        attributes[attName] = FloatProperty(name=name, default=param['value'], max=maxValue,
                                            min=param['minValue'], update=RunUpdate(param, sbsarData))
    elif pType == 'string':
        attributes[attName] = StringProperty(name=name, default=param['value'], update=RunUpdate(param, sbsarData))
    else:
        print('Invalid property type: ' + pType)


def CreateVectorProperty(attributes, sbsarData, attName, name, param, vValue, dimensions, maxValue, subtype='NONE'):
    """ Create a vector parameter for either int or float depending on isInt flag """
    vecType = param['type'].lower()
    minValue = param['minValue'][0]
    if vecType.startswith('int'):
        attributes[attName] = IntVectorProperty(name=name, size=dimensions, subtype=subtype,
                                                default=vValue, max=maxValue, min=minValue,
                                                update=RunUpdate(param, sbsarData))
    else:
        attributes[attName] = FloatVectorProperty(name=name, size=dimensions, subtype=subtype,
                                                  default=vValue, max=maxValue, min=minValue,
                                                  update=RunUpdate(param, sbsarData))


def SetupColor(attributes, sbsarData, attName, param):
    """ Setup a Color picker Attribute """
    pType = param['type']
    minValue = param['minValue']
    maxValue = param['maxValue']
    pValue = param['value']
    name = GetParamName(param)
    if pType == 'float':
        if maxValue <= 0:
            maxValue = 1
        attributes[attName] = FloatProperty(name=name, default=pValue, max=maxValue, min=minValue,
                                            update=RunUpdate(param, sbsarData))
    elif pType.startswith('float'):
        vValue = Vector(param['value'])
        dimensions = len(vValue)
        if maxValue[0] <= 0:
            maxValue[0] = 1
        attributes[attName] = FloatVectorProperty(name=name, subtype='COLOR', size=dimensions,
                                                  min=minValue[0], max=maxValue[0], default=vValue,
                                                  update=RunUpdate(param, sbsarData))
    else:
        print('Unsupported color type: ' + pType)


def SetupEnum(attributes, sbsarData, attName, param):
    """ Setup a enumerator Attribute """
    items = []
    for i, item in enumerate(param['enumValues']):
        items.append((str(item['first']), str(item['second']), '', item['first']))
    attributes[attName] = EnumProperty(name=attName, items=items, default=str(param['value']),
                                       update=RunUpdate(param, sbsarData))


def SubstanceParentPanelFactory(space, sid):
    """ Create the substance parameter parent panel """
    name = space + '_' + sid[-4:]
    suffix = re.sub('[^0-9a-zA-Z]+', '_', name)

    class SUBSTANCE_PT_Parent(bpy.types.Panel):
        bl_idname = 'SUBSTANCE_PT_Parent_%s' % suffix
        bl_space_type = space
        bl_label = 'Substance Parameters'
        bl_region_type = 'UI'
        bl_category = 'Substance 3D'
        sbsarId = sid

        @classmethod
        def poll(cls, context):
            if len(SbsarParamMgr.sbsarId) > 0:
                sbsarId = getattr(cls, 'sbsarId', '')
                if sbsarId == SbsarParamMgr.sbsarId:
                    return True
            return False

        def draw(self, context):
            pass

    return SUBSTANCE_PT_Parent


class SUBSTANCE_MT_ExtendedPresetOptions(Menu):
    bl_idname = 'SUBSTANCE_MT_ExtendedPresetOptions'
    bl_label = ""
    bl_description = 'Additional Preset Options'
    bl_options = {'REGISTER'}
    enableSinglePresetOps = False

    def draw(self, context):
        col = self.layout.column()
        if SUBSTANCE_MT_ExtendedPresetOptions.enableSinglePresetOps:
            col.operator('substance.export_sbsprs').description_arg = True
        else:
            disabledCol = col.column()
            disabledCol.enabled = False
            disabledCol.operator('substance.export_sbsprs').description_arg = False
        if SUBSTANCE_MT_ExtendedPresetOptions.enableSinglePresetOps:
            col.operator('substance.delete_preset').description_arg = True
        else:
            disabledCol = col.column()
            disabledCol.enabled = False
            disabledCol.operator('substance.delete_preset').description_arg = False


def SBSARParamPanelFactory(space, name, propertySuffix, parentId, sbData):
    """ Create a Parameter Panel """

    # replace any non alphanumeric character with an underscore
    spaceName = space + '_' + name + '_' + sbData.id[-4:]
    suffix = re.sub('[^0-9a-zA-Z]+', '_', spaceName)

    class SUBSTANCE_PT_Parameter(bpy.types.Panel):
        bl_idname = 'SUBSTANCE_PT_Parameter_%s' % suffix
        bl_parent_id = parentId
        bl_space_type = space
        bl_label = name
        bl_region_type = 'UI'
        bl_category = 'Substance 3D'
        sbsarData = sbData
        sbsarId = sbData.id

        @classmethod
        def poll(cls, context):
            if len(SbsarParamMgr.sbsarId) > 0:
                sbsarId = getattr(cls, 'sbsarId', '')
                if sbsarId == SbsarParamMgr.sbsarId:
                    return True
                return False

        def draw(self, context):
            """ draw the panel and all operators assigned to it """
            col = self.layout.column(align=True)
            name = self.bl_label + propertySuffix + self.sbsarId[-4:]
            propertyGroup = getattr(bpy.context.scene, name)
            enableHeight = False
            cachedWidthValue = None
            for p in propertyGroup.__annotations__:
                row = col.row()
                if p == 'res_link':
                    enableHeight = not getattr(propertyGroup, p)
                    row.label(text='Output Resolution')
                    row.prop(propertyGroup, p)
                elif p == 'res_width':
                    cachedWidthValue = p
                    col.prop(propertyGroup, p)
                elif p == 'res_height':
                    if enableHeight:
                        row.prop(propertyGroup, p)
                    else:
                        row.prop(propertyGroup, cachedWidthValue, text='Height')
                    row.enabled = enableHeight
                elif p == 'Preset':
                    row.prop(propertyGroup, p)
                    row2 = col.row()
                    row2.operator('substance.load_sbsprs', text='Load')
                    row2.operator('substance.name_sbsprs', text='Save')
                    val = getattr(propertyGroup, p, None)
                    SUBSTANCE_MT_ExtendedPresetOptions.enableSinglePresetOps = val in self.sbsarData.addedPresetNames
                    row2.menu(SUBSTANCE_MT_ExtendedPresetOptions.bl_idname, icon='TRIA_DOWN')
                else:
                    if p == '$randomseed':
                        row.label(text='Random Seed')
                        row.prop(propertyGroup, p, text='')
                        row = col.row()
                        sp = row.split(factor=0.5)
                        sp.label(text='')
                        sp.operator('substance.randomize_seed', text='Randomize')
                    elif p != 'sbsarId':
                        txt = p
                        useSlider = False
                        if txt.endswith(SLIDER_SUFFIX):
                            useSlider = True
                            txt = txt[:-(len(SLIDER_SUFFIX))]
                        if PROP_ID_NAME_SEPARATOR in txt:
                            txt = txt.split(PROP_ID_NAME_SEPARATOR)[1]
                        row.label(text=txt)
                        row.prop(propertyGroup, p, text='', slider=useSlider)
                col.separator(factor=0.5)

    return SUBSTANCE_PT_Parameter


class SbsarParamMgr():
    """ Manage the SBSAR parameters """
    panelAndPropertyClasses = {}        # Added panels for cleanup
    addedAttributes = []                # Added parameter attributes to the scene stored for cleanup
    propertySuffix = '_props'           # Property suffix added to generated class names
    sbsarClient = None                  # Cient connected to the SRE to send updates
    sbsarId = ''                        # The SBSAR Currently being displayed

    # Disable updating preset values when automatically changing the dropdown selection
    enablePresetChange = True

    # Show the extended preset options
    show_extended_presetoptions = False

    @classmethod
    def setup(cls, client):
        """ Setup the Paramter Manager vars """
        cls.sbsarClient = client

    def unregister(self):
        """ cleanup """
        SbsarParamMgr.sbsarId = ''
        for panel in self.panelAndPropertyClasses:
            try:
                self.unregisterPanel(self.panelAndPropertyClasses[panel])
            except Exception:
                print('failed to unregister panel: ' + str(panel))
                pass
        for att in self.addedAttributes:
            try:
                delattr(bpy.types.Scene, att)
            except Exception:
                print('failed to delete attribute: ' + str(att))
                pass
        self.addedAttributes.clear()
        self.panelAndPropertyClasses = {}

    def unregisterPanel(self, panel):
        """ Unregister the current parameter panels """
        for pcls in panel:
            try:
                bpy.utils.unregister_class(pcls)
            except Exception:
                print('failed to unregister: ' + str(pcls))
                pass

    def buildGuiParameterGroups(self, client, sbsarData):
        """ Build the various parameter groups to be stored in the SBSAR Data GUI Params"""
        if sbsarData is None or sbsarData.parameters is None:
            print('No Sbsar parameters to build UI')
            return

        # build the parameter panels
        SbsarParamMgr.sbsarClient = client
        SbsarParamMgr.sbsarId = sbsarData.id
        sbsarData.populateGuiParameters()

    def populatePanels(self, context, sbsarData, guiParams, spaces, presetName, uiOutputCallback):
        """ Populate the parameter panels from the SBSAR Data GUI Params"""
        SbsarParamMgr.sbsarId = sbsarData.id

        if sbsarData.id not in self.panelAndPropertyClasses:
            self.panelAndPropertyClasses[sbsarData.id] = []

            # add the panel to each space
            for space in spaces:
                parentPanel = None

                for group in guiParams:
                    addedClass = False
                    isGraphParameters = False

                    # create param group
                    clsName = self.getPropClassName(group, self.propertySuffix, sbsarData.id[-4:])
                    if clsName not in self.addedAttributes:
                        paramPropertyGroup = BuildPropertyGroupClass(clsName, self, sbsarData, guiParams[group],
                                                                     group == OUTPUT_GROUP_NAME, presetName,
                                                                     uiOutputCallback)
                        if paramPropertyGroup is not None:
                            bpy.utils.register_class(paramPropertyGroup)
                            setattr(bpy.types.Scene, clsName, PointerProperty(name=clsName, type=paramPropertyGroup))
                            self.addedAttributes.append(clsName)
                            self.panelAndPropertyClasses[sbsarData.id].append(paramPropertyGroup)

                    # Graph parameters stays outside the parent parameter group
                    if group == 'Graph Parameters':
                        panelClass = SBSARParamPanelFactory(space[1], group, self.propertySuffix, '', sbsarData)
                        addedClass = True
                        isGraphParameters = True
                    elif group != CHANNEL_GROUP_NAME:
                        if parentPanel is None:
                            parentPanel = self.createParentPanel(space, sbsarData.id)
                        panelClass = SBSARParamPanelFactory(space[1], group, self.propertySuffix, parentPanel,
                                                            sbsarData)
                        addedClass = True

                    # register any added class
                    if addedClass:
                        bpy.utils.register_class(panelClass)
                        self.panelAndPropertyClasses[sbsarData.id].append(panelClass)
                        if isGraphParameters:
                            self.setProperty(clsName, 'Preset', presetName)

    def createParentPanel(self, space, sbsarId):
        """ create parent parameter panel """
        parentPanel = SubstanceParentPanelFactory(space[1], sbsarId)
        bpy.utils.register_class(parentPanel)
        self.panelAndPropertyClasses[sbsarId].append(parentPanel)
        return parentPanel.bl_idname

    def updateProperties(self, sbsarData, useCustomOutputs):
        """ Update the UI property list with the latest parameter data """
        propGroups = GetPropertyGroupsFromId(sbsarData.id)

        # loop though all the property groups associated with this sbsar
        for propGroup in propGroups:

            # loop through all parameters in each property group
            for param in sbsarData.parameters:
                paramName = GetParamName(param)

                # update the property values
                propGroupName = propGroup.__class__.__name__
                if propGroupName.startswith(OUTPUT_GROUP_NAME):
                    self.updateOutputProperty(sbsarData, useCustomOutputs, propGroup, paramName)
                else:
                    if paramName == "$outputsize":
                        self.updateResolutionProperty(propGroup, param)
                    else:
                        self.updatePropertyFromParam(propGroup, paramName, param)

    def updateOutputProperty(self, sbsarData, useCustomOutputs, propGroup, paramName):
        """ Properly update an output channel property """
        if propGroup:
            try:
                if useCustomOutputs:
                    setattr(propGroup, paramName, sbsarData.customOutputPresetValues[paramName])
                else:
                    setattr(propGroup, paramName, True)
            except Exception:
                pass

    def updateResolutionProperty(self, propGroup, param):
        """ Properly update the resolution property """
        if propGroup:
            try:
                setattr(propGroup, 'res_width', str(param['value'][0]))
                setattr(propGroup, 'res_height', str(param['value'][1]))
            except Exception:
                print(str(propGroup) + ' -- No resolution params')

    def updatePropertyFromParam(self, propGroup, paramName, param):
        """ Update generic properties """
        if propGroup:
            prop = propGroup.__annotations__.get(paramName, None)
            if prop:
                attType = param['guiWidget']
                if IsEnum(attType):
                    setattr(propGroup, paramName, str(param['value']))
                else:
                    if IsVector(param['type']):
                        vValue = Vector(param['value'])
                        setattr(propGroup, paramName, vValue)
                    else:
                        setattr(propGroup, paramName, param['value'])

    def ensureOpenGL(self, paramList, sbsarid):
        """ force normal_format parameter to OpenGL """
        for param in paramList:
            if param['identifier'] == 'normal_format':
                self.updateParameter(sbsarid, param['id'], 1, False, False)

    @classmethod
    def setProperty(cls, classname, propName, value):
        """ Set the value of a specific property """
        graphProps = getattr(bpy.context.scene, classname, None)
        if graphProps:
            if hasattr(graphProps, propName):
                setattr(graphProps, propName, value)
        else:
            print('Unable to update ' + propName + ' for: ' + classname)

    @classmethod
    def getProperty(cls, classname, propName):
        """ Get the value of a specific property """
        value = None
        graphProps = getattr(bpy.context.scene, classname, None)
        if graphProps:
            value = getattr(graphProps, propName, None)
        return value

    @classmethod
    def updateParameter(cls, sbsarId, paramId, value, threaded, customParameter):
        """ Update a parameter value """
        if cls.sbsarClient:
            cls.sbsarClient.sendParamUpdate(sbsarId, paramId, value, threaded)
            if customParameter:
                cls.setPresetUIToCustom(sbsarId)
        else:
            print('Cannot update parameter -- no SBSAR Client')
        return None

    @classmethod
    def setPresetUIToCustom(cls, sbsarId):
        """ Set the Preset UI dropdown to Custom """

        # disable any property changes from switching the UI to the Custom preset
        SbsarParamMgr.allowPresetChange(False)
        sbsar = bpy.context.scene.loadedSbsars[bpy.context.scene.sbsar_index]
        if sbsar.presetName != 'Custom':
            sbsar.presetName = 'Custom'
            propGroups = GetPropertyGroupsFromId(sbsarId)
            for propGroup in propGroups:
                prop = propGroup.__annotations__.get('Preset', None)
                if prop:
                    setattr(propGroup, 'Preset', 'Custom')
        SbsarParamMgr.allowPresetChange(True)

    @classmethod
    def loadPreset(cls, preset, sbsarid):
        """ submit a preset to the remote engine """
        if len(preset) > 0:
            try:
                presetDict = ast.literal_eval(preset)
                for i, value in enumerate(presetDict.values()):
                    if cls.sbsarClient:
                        cls.sbsarClient.loadPreset(sbsarid, value, 0)
                    else:
                        print('No Substance 3D material Client -- unable to load preset')
            except Exception as e:
                print('Could not apply preset: ' + str(preset))
                print(e)
        else:
            cls.sbsarClient.loadPreset(sbsarid, '', 0)

    @classmethod
    def getPropClassName(cls, name, suffix, uniqueIdent):
        """ Return the class name """
        return name + suffix + uniqueIdent

    @classmethod
    def allowPresetChange(cls, allow):
        """ Enable disable preset parameter updates"""
        SbsarParamMgr.enablePresetChange = allow

    @classmethod
    def getResolutionLinkValue(cls, sbsarData):
        """ Return the value of the resolution linked property """
        value = True
        graphClassName = cls.getPropClassName('Graph Parameters', cls.propertySuffix, sbsarData.id[-4:])
        isLinked = cls.getProperty(graphClassName, 'res_link')
        if isLinked is not None:
            value = isLinked
        return value

    @classmethod
    def setResolutionLinkValue(cls, sbsarData, linkVal):
        """ Set the value of the resolution linked property """
        graphClassName = cls.getPropClassName('Graph Parameters', cls.propertySuffix, sbsarData.id[-4:])
        cls.setProperty(graphClassName, 'res_link', linkVal)
