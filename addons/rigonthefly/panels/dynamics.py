import bpy
import math

from .main import ToolPanel, separator
from ..core.icon_manager import Icons
from ..core import dynamics

class DynamicsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_dynamics'
    bl_label = 'Dynamics On Transforms'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop(scene, 'rotf_dynamics_start', text="Start")
        row.prop(scene, 'rotf_dynamics_end', text="End")
        col.prop(scene, 'rotf_blend_frame', text="Start Blend Frame")

        col = layout.column(align=True)

        col.prop(scene, 'rotf_frequency', text="Frequency")
        col.prop(scene, 'rotf_damping', text="Damp")
        col.prop(scene, 'rotf_response', text="Response")

        col.template_curve_mapping(dynamicsCurveWidget(self, context), "mapping")

        col = layout.column(align=True)

        row = col.row(align=True)
        dynamicsOnLocation = row.operator('rotf.dynamics_on_transforms', text="Loc", icon='CON_LOCLIMIT')
        dynamicsOnLocation.transformsType = "location"

        dynamicsOnRotation = row.operator('rotf.dynamics_on_transforms', text="Rot", icon='CON_ROTLIMIT')
        dynamicsOnRotation.transformsType = "rotation"

        dynamicsOnScale = row.operator('rotf.dynamics_on_transforms', text="Scale", icon='CON_SIZELIMIT')
        dynamicsOnScale.transformsType = "scale"

        row = col.row(align=True)
        dynamicsOnSelection = row.operator('rotf.dynamics_on_transforms', text="Selected Transforms")
        dynamicsOnSelection.transformsType = "selection"

def dynamicsCurveWidget(self, context):
    nodeGroup = bpy.data.node_groups.get('RotFDynamicsCurveData')
    if not nodeGroup:
        nodeGroup = bpy.data.node_groups.new('RotFDynamicsCurveData', 'ShaderNodeTree')
    rgbCurveNode = nodeGroup.nodes.get('RGB Curves')
    if not rgbCurveNode:
        rgbCurveNode = nodeGroup.nodes.new('ShaderNodeRGBCurve')
    return rgbCurveNode

def dynamicsCurveUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    rgbCurveNode = bpy.data.node_groups['RotFDynamicsCurveData'].nodes['RGB Curves']
    cCurve = rgbCurveNode.mapping.curves[3]

    frameStart = scene.rotf_dynamics_start
    frameEnd = scene.rotf_dynamics_end + 1
    numberOfFrames = frameEnd-frameStart

    t = 1/scene.render.fps

    newPointsList = findNewKeyframesList(numberOfFrames, t)
    newPointsList = convergeToEndFrame(newPointsList)

    #remove all but two points on the curve
    while len(cCurve.points) > 2:
        lastPoint = cCurve.points[-1]
        cCurve.points.remove(lastPoint)

    normalizeList(newPointsList)

    setNewPoints(cCurve, newPointsList)

    verticalFraming(rgbCurveNode, newPointsList)

    rgbCurveNode.mapping.update()

def findNewKeyframesList(numberOfFrames, t):
    newPointsList = list()
    
    scene = bpy.context.scene

    f = scene.rotf_frequency
    z = scene.rotf_damping
    r = scene.rotf_response

    k1 = z/(math.pi*f)
    k2 = 1/((2*math.pi*f)*(2*math.pi*f))
    k3 = r*z/(2*math.pi*f)

    xp = 0
    x = 0

    y = x
    yd = (x - xp)/t

    for f in range(numberOfFrames):
        y = y + t * yd

        k2_stable = max(k2, 1.1 * (t*t/4 + t*k1/2)) #clamp k2 to guarantee stability
        xd = (x - xp)/t
        yd = yd + t * (x + k3*xd - y - k1*yd)/k2_stable
        
        newPointsList.append([f, y])

        xp = x
        x = 1.0

    return newPointsList

def convergeToEndFrame(newPointsList):
    scene = bpy.context.scene
    blendFrame = scene.rotf_blend_frame

    for i, fy in enumerate(newPointsList):
        f = fy[0]
        y = fy[1]

        if f == blendFrame:
            startBlendIndex = i

            if (len(newPointsList)- 1 - startBlendIndex) == 0:
                return newPointsList

        if f >= blendFrame:
            x = 1.0 #current frame value
            y = y #new frame value from newKeyframesList
            blendFactor=(i - startBlendIndex)/(len(newPointsList)- 1 - startBlendIndex) #blend factor
            blendFactor=dynamics.easeInOutQuad(blendFactor)
            blendedY = (blendFactor * x) + ((1-blendFactor) * y) #lerp blend
            newPointsList[i] = [f, blendedY]

    return newPointsList

def normalizeList(newPointsList):
    #find minimum value of x and y 
    minY = 0.0
    maxY = 1.0

    xRange = len(newPointsList)
    yRange = maxY - minY

    #normalize x and y values
    for i, xy in enumerate(newPointsList):
        x = xy[0]
        y = xy[1]

        normalizedX = x/xRange
        normalizedY = (y-minY)/yRange

        newPointsList[i] = [normalizedX, normalizedY]

    return newPointsList

def setNewPoints(curve, newPointsList):
    for i, xy in enumerate(newPointsList):
        x = xy[0]
        y = xy[1]

        if i < 2:
            curve.points[i].location[0] = x
            curve.points[i].location[1] = y
        else:
            curve.points.new(x, y)

def verticalFraming(rgbCurveNode, newPointsList):
    minY = 0.0
    maxY = 1.0
    for x, y in newPointsList:
        if y < minY:
            minY = y
        if y > maxY:
            maxY = y

    rgbCurveNode.mapping.clip_min_y = minY - 0.2
    rgbCurveNode.mapping.clip_max_y = maxY + 0.2
    rgbCurveNode.mapping.reset_view()
