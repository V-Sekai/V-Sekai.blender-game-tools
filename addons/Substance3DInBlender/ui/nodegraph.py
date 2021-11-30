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


# Substance Node Graph
# 02/23/2021
import bpy
import bmesh
from mathutils import Vector
import os

# UI layout parameters
UI_DispNodeYPos = -350
UI_TextureYPosIncrement = -275
UI_TextureXPosOffset = -575
UI_NormalNodeXPosOffset = -250
UI_TexCoordXOffset = -200
UI_MappingXPosOffset = 400
UI_InputNodeXPosOffset = -1000
UI_InputNodeYPosOffset = -200
UI_MappingWidth = 240
UI_ReroutingXPosOffset = -675
UI_ValueNodeYOffset = 150
UI_ValueNodeYIncrement = 200
UI_SBSAR_OutputXOffset = 200
UI_NODEGROUP_XOffset = 300

# UI Socket Name
UV_SOCKET_NAME = 'UV'


def GetPropertyClassKeywordAttribute(propertyClass, attribute):
    """ Get the keyword attribute from the property class """
    if hasattr(propertyClass, 'keywords'):
        # starting with blender 2.93 use keywords
        return propertyClass.keywords[attribute]
    else:
        # no longer supported as of blender 2.93
        return propertyClass[1][attribute]


class SbsarOutputLink():
    """ The data needed to create/destroy an output link """

    def __init__(self, to, fr):
        """ Initialize the data """
        self.toSocket = to
        self.fromSocket = fr
        self.link = None
        self.enabled = False

    def addLink(self, links):
        """ Add a blender UI link """
        try:
            self.link = links.new(self.fromSocket, self.toSocket)
            self.enabled = True
        except Exception as e:
            print('Faled to add link: ' + str(e))

    def removeLink(self, links):
        """ Remove a blender UI Link """
        try:
            if self.link:
                links.remove(self.link)
            self.enabled = False
        except Exception as e:
            print('Failed to remove link: ' + str(e))


def CreateMaterial(paramManager, sbsarData, context, texture_preference_map, obj):
    """ Create a blender material from the sbsar data """
    if obj is None:
        print('Loading an SBSAR requires an object in scene in order to create the blender material')
        return

    # load the material
    mat = bpy.data.materials.get('sbsarData.name')
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name=sbsarData.name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes['Principled BSDF']
    shaderPos = bsdf.location

    # create substance node group
    sbsar_name = sbsarData.name
    substanceNodeGroup = bpy.data.node_groups.new(type='ShaderNodeTree', name=sbsar_name)
    substanceNodes = substanceNodeGroup.nodes

    # setup group output node
    output_node = substanceNodes.new('NodeGroupOutput')
    output_node.location = (UI_SBSAR_OutputXOffset, 0)

    # cache the newly created nodes to create the proper UI mappings
    newTexNodes = []
    newValNodes = []
    textureIndex = 0
    for blender_texture_prop in texture_preference_map.__annotations__:
        blendTexProp = texture_preference_map.__annotations__[blender_texture_prop]
        prop_name = GetPropertyClassKeywordAttribute(blendTexProp, 'name')

        # Create Blender nodes form the SBSAR output data
        if prop_name in sbsarData.mapped_outputs.keys():
            texPath, output_value, id = sbsarData.mapped_outputs[prop_name]

            # Load the mapped texture
            if len(texPath) > 0:
                if os.path.exists(texPath):
                    texNode = substanceNodes.new('ShaderNodeTexImage')

                    # the node name is in two parts the first is used for relinking upon loading a blend file
                    # the sceond part of the name is the property ID, used when receiving updates from the Tools
                    texNode.name = sbsarData.id + '.' + str(id)
                    texNode.image = bpy.data.images.load(texPath)
                    texNode.label = prop_name
                    yPos = shaderPos[1] + (textureIndex * UI_TextureYPosIncrement)
                    texNode.location = Vector((UI_TextureXPosOffset, yPos))

                    # setup normal node
                    if prop_name == 'Normal' or prop_name == 'Clearcoat Normal':
                        normalNode = substanceNodes.new(type='ShaderNodeNormalMap')
                        substanceNodeGroup.outputs.new('NodeSocketVector', prop_name)
                        substanceNodeGroup.links.new(normalNode.inputs[1], texNode.outputs[0])
                        normalNode.location = Vector((UI_NormalNodeXPosOffset, yPos))
                        substanceNodeGroup.links.new(normalNode.outputs[0], output_node.inputs[texNode.label])

                    # setup displacement node
                    elif prop_name == 'Displacement':
                        dispNode = nodes.new(type='ShaderNodeDisplacement')
                        dispNode.name = 'SBSARDispNode'
                        dispNode.inputs['Scale'].default_value = texture_preference_map.displacementScale
                        substanceNodeGroup.outputs.new('NodeSocketVector', 'Height')
                        substanceNodeGroup.links.new(texNode.outputs[0],  output_node.inputs['Height'])
                        dispNode.location = Vector((bsdf.location[0], UI_DispNodeYPos))
                        links.new(dispNode.outputs['Displacement'], nodes['Material Output'].inputs['Displacement'])

                    # setup all other output nodes
                    else:
                        substanceNodeGroup.outputs.new('NodeSocketColor', prop_name)
                        substanceNodeGroup.links.new(texNode.outputs['Color'], output_node.inputs[texNode.label])

                    SetTexNodeColorSpace(texNode)
                    sbsarData.textureNodes.append(texNode)
                    newTexNodes.append(texNode)
                    textureIndex += 1
                else:
                    print('Texture does not exist: ' + texPath)
                    return None

            # Load the value output
            elif output_value is not None:
                valueNode = substanceNodes.new('ShaderNodeValue')
                valueNode.name = str(id)
                valueNode.label = prop_name
                valueNode.outputs[0].default_value = output_value
                substanceNodeGroup.outputs.new('NodeSocketFloat', prop_name)
                substanceNodeGroup.links.new(valueNode.outputs['Value'], output_node.inputs[valueNode.label])
                sbsarData.valueNodes.append(valueNode)
                newValNodes.append(valueNode)
            else:
                print('No Outputs for Prop: ' + prop_name)

    # add the newly created blender material to the object
    if len(newTexNodes) > 0:

        # add the material to the object
        obj.data.materials.append(mat)

        # set the active material index to the newly created material
        obj.active_material_index = len(obj.data.materials) - 1

        if bpy.context.object is None:
            context.view_layer.objects.active = obj
            obj.select_set(True)

        # apply material to all faces which must be done in 'EDIT' Mode
        currentMode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            face.material_index = obj.active_material_index
        bpy.ops.object.mode_set(mode=currentMode)

        # build the Material evel group node
        group_node = nodes.new('ShaderNodeGroup')
        group_node.name = sbsar_name + '_sbsar_group'
        group_node.node_tree = substanceNodeGroup
        group_node.location = (shaderPos[0] - UI_NODEGROUP_XOffset, shaderPos[1])
        group_node.select = True
        nodes.active = group_node

        # link up the graph
        DrawMappingUI(context, substanceNodeGroup, bsdf.location[0], shaderPos[1], newTexNodes, newValNodes)
        CreateUVMapping(mat, group_node, newTexNodes)

        # setup the group outputs and map to the Shader
        for output in group_node.outputs:
            enabled = True
            linkName = output.name
            if output.name in sbsarData.outputLinks:
                enabled = sbsarData.outputLinks[output.name].enabled

            if output.name == 'Height':
                toNode = dispNode.inputs['Height']
                linkName = 'Displacement'
            else:
                toNode = bsdf.inputs[output.name]
            oLink = SbsarOutputLink(toNode, output)
            if enabled:
                oLink.addLink(links)
            sbsarData.outputLinks[linkName] = oLink
        return mat
    return None


def CreateUVMapping(mat, groupNode, texNodes):
    """ Create a the blender UV Mapping nodes """

    # create the input node for the substance group if needed
    groupInputNode = groupNode.node_tree.nodes.get('NodeGroupInput', None)
    if not groupInputNode:
        groupInputNode = groupNode.node_tree.nodes.new('NodeGroupInput')
        groupInputNode.location = Vector((UI_InputNodeXPosOffset, UI_InputNodeYPosOffset))
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Create the Mapping Node
    mapping = nodes.new(type='ShaderNodeMapping')
    mapping.location = Vector((groupNode.location[0] - UI_MappingXPosOffset, groupNode.location[1]))
    mapping.width = UI_MappingWidth

    # Create the UV Texture Coordinate node
    textureInput = nodes.new(type='ShaderNodeTexCoord')
    textureInput.location = mapping.location + Vector((UI_TexCoordXOffset, 0))

    # Link the nodes
    links.new(mapping.inputs[0], textureInput.outputs[2])

    # Create frame around Mapping and TexCoord
    frame = nodes.new(type='NodeFrame')
    frame.label = 'Mapping'
    mapping.parent = frame
    textureInput.parent = frame
    frame.update()

    # create the input socket to the substance node and connect
    groupNode.inputs.new('NodeSocketVector', UV_SOCKET_NAME)
    links.new(groupNode.inputs[UV_SOCKET_NAME], mapping.outputs[0])

    # link the UV mapping to all the texture nodes
    for texNode in texNodes:
        groupNode.node_tree.links.new(texNode.inputs['Vector'], groupInputNode.outputs[UV_SOCKET_NAME])


def DrawMappingUI(context, node_tree, xpos, ypos, newTexNodes, newValNodes):
    """ Configure the graph for the substance group node """

    # Create frame around tex coords and mapping
    nodes = node_tree.nodes

    # Create frame around texture nodes
    if len(newTexNodes) > 0:
        texFrame = nodes.new(type='NodeFrame')
        texFrame.label = 'Textures'
        for tnode in newTexNodes:
            tnode.parent = texFrame
        texFrame.update()

    # place the value nodes together above the textures
    if len(newValNodes) > 0:
        valueFrame = nodes.new(type='NodeFrame')
        valueFrame.label = 'Values'

        yPos = texFrame.location[1] - UI_ValueNodeYOffset
        for vNode in newValNodes:
            vNode.location = Vector((UI_TextureXPosOffset, yPos))
            yPos -= UI_ValueNodeYIncrement
            vNode.parent = valueFrame
        valueFrame.update()
    return {'FINISHED'}


def SetTexNodeColorSpace(texNode):
    """ set Base Color to sRGB and all others to Non-Color """
    try:
        if texNode.label == 'Base Color':
            texNode.image.colorspace_settings.name = 'sRGB'
        else:
            texNode.image.colorspace_settings.name = 'Non-Color'
    except Exception:
        print('Non-Standard Color Space Detected -- Please manually select')
