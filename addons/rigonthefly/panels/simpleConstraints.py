import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons

class SimpleConstraintsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_simpleConstraints'
    bl_label = 'Simple Constraints'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        selectedPBoneList = bpy.context.selected_pose_bones
        activePBone = bpy.context.active_pose_bone

        scene = context.scene
        layout = self.layout

        canCopyTransforms = False
        canAim = False
        if bpy.context.mode == 'POSE':
            if len(bpy.context.selected_pose_bones) > 1:
                if scene.rotf_simple_copy_location or scene.rotf_simple_copy_rotation or scene.rotf_simple_copy_scale:
                    canCopyTransforms = True
                canAim = True

        row = layout.row(align=True)
        row.prop(scene, 'rotf_simple_copy_location', text="Location")
        row.prop(scene, 'rotf_simple_copy_rotation', text="Rotation")
        row.prop(scene, 'rotf_simple_copy_scale', text="Scale")
        row = layout.row(align=True)
        row.operator('rotf.simple_copy_transforms', text="Copy Transforms")
        row.enabled = canCopyTransforms

        #row = layout.row(align=True)
        #row.label(text="Aim")
        row = layout.row(align=True)
        row.operator('rotf.simple_aim', text="Aim")
        row.prop(scene, 'rotf_simple_aim_axis')
        #row.enabled = canAim

        #row = layout.row(align=True)
        #row.label(text="Roll")

        row = layout.row(align=True)
        row.prop(scene, 'rotf_simple_influence')

        row = layout.row(align=True)
        row.operator('rotf.remove_simple_constraints', text="Remove")
        row.operator('rotf.bake_simple_constraints', text="Bake")
        row.enabled = True

        