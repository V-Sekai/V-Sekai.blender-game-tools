bl_info = {
    "name": "Bone Rest Info",
    "author": "Tokage IT Lab.",
    "version": (1, 1),
    "blender": (2, 91, 0),
    "location" : "View3D > Property Panel > Item",
    "description": "Displays bone rest rotation, i.e. the orientation of the local axis of the bone",
    "category": "3D View"
}


import bpy
import math
import mathutils
from decimal import *


translation_dict = {
    "ja_JP": {
        ("*", "Displays bone rest rotation, i.e. the orientation of the local axis of the bone"): "ボーンのレスト時の回転値（ボーンのローカル軸の方向）を表示します",
        ("*", "World space"): "空間",
        ("*", "Rotation mode"): "回転モード",
        ("*", "Coordinate system"): "座標系",
        ("*", "Bone Rest Rotation:"): "ボーンの軸方向",
        ("*", "Need to select only 1 bone"): "ボーンを１つだけ選択する必要があります",
        ("*", "Need to enable bone edit mode"): "編集モードである必要があります",
        ("*", "R-Hand Z-UP (Blender)"): "右手系 Z-UP (Blender)",
        ("*", "R-Hand Y-UP (OpenGL)"): "右手系 Y-UP (OpenGL)"
    }
}


class SBR_Props(bpy.types.PropertyGroup):
    world_space: bpy.props.EnumProperty(
        name="World Space",
        description=bpy.app.translations.pgettext("World space"),
        items = (
            ("Global", "Global", ""),
            ("Local", "Local", "")
        ),
        default = 1
    )
    rotation_mode: bpy.props.EnumProperty(
        name="Rotation Mode",
        description=bpy.app.translations.pgettext("Rotation mode"),
        items = (
            ("QUATERNION", "Quartanion (WXYZ)", ""),
            ("XYZ", "XYZ Euler", ""),
            ("XZY", "XZY Euler", ""),
            ("YXZ", "YXZ Euler", ""),
            ("YZX", "YZX Euler", ""),
            ("ZXY", "ZXY Euler", ""),
            ("ZYX", "ZYX Euler", ""),
            ("AXIS_ANGLE", "Axis Angle", ""),
            ("MATRIX", "Matrix", "")
        ),
        default = 5
    )
    coordinate_system: bpy.props.EnumProperty(
        name="Coordinate System",
        description=bpy.app.translations.pgettext("Coordinate system"),
        items = (
            ("RH_YU", bpy.app.translations.pgettext("R-Hand Z-UP (Blender)"), ""),
            ("RH_ZU", bpy.app.translations.pgettext("R-Hand Y-UP (OpenGL)"), "")
        ),
        default = 1
    )


class SBR_PT_panel(bpy.types.Panel):
    bl_label = "Bone Rest Info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        sbr_info(self, context)


def trunc(value):
    return str(Decimal(str(value)).quantize(Decimal("0.001"),rounding=ROUND_HALF_UP))


def sbr_info(self, context):
    sc = context.scene
    layout = self.layout
    sbr_column = layout.column(align=True)
    sbr_column.label(text=bpy.app.translations.pgettext("Bone Rest Rotation:"))
    sbr_box = sbr_column.box()
    sbr_box_column = sbr_box.column(align=True)
    if context.active_object.mode == "EDIT":
        bone = context.active_bone
        if (bone):
            bone_rotation = bone.matrix
            if sc.SBR_Props.world_space == "Local":
                if (bone.parent):
                    parent_mat = bone.parent.matrix
                    parent_mat.invert()
                    bone_rotation = parent_mat @ bone_rotation
                else:
                    # convert coordinate system
                    if sc.SBR_Props.coordinate_system == "RH_ZU":
                        transform_mat = mathutils.Matrix((
                            (1,0,0,0),
                            (0,0,1,0),
                            (0,-1,0,0),
                            (0,0,0,1)
                        ))
                        bone_rotation = transform_mat @ bone_rotation
            else:
                # convert coordinate system
                if sc.SBR_Props.coordinate_system == "RH_ZU":
                    transform_mat = mathutils.Matrix((
                        (1,0,0,0),
                        (0,0,1,0),
                        (0,-1,0,0),
                        (0,0,0,1)
                    ))
                    bone_rotation = transform_mat @ bone_rotation
            # convert rotation type
            if sc.SBR_Props.rotation_mode == "MATRIX":
                labels = ("X", "Y", "Z")
                for i in range(3):
                    sbr_box_column_row = sbr_box_column.row(align=True)
                    for j in range(3):
                        sbr_box_column_row.label(text=labels[j] + ": " + trunc(bone_rotation[j][i]))
            elif sc.SBR_Props.rotation_mode == "QUATERNION":
                bone_rotation = bone_rotation.to_quaternion()
                sbr_box_column.label(text="W: " + trunc(bone_rotation.w))
                sbr_box_column.label(text="X: " + trunc(bone_rotation.x))
                sbr_box_column.label(text="Y: " + trunc(bone_rotation.y))
                sbr_box_column.label(text="Z: " + trunc(bone_rotation.z))
            elif sc.SBR_Props.rotation_mode == "AXIS_ANGLE":
                bone_rotation = bone_rotation.to_quaternion().to_axis_angle()
                sbr_box_column.label(text="W: " + trunc(math.degrees(bone_rotation[1])) + "°")
                sbr_box_column.label(text="X: " + trunc(bone_rotation[0].x))
                sbr_box_column.label(text="Y: " + trunc(bone_rotation[0].y))
                sbr_box_column.label(text="Z: " + trunc(bone_rotation[0].z))
            else:
                bone_rotation = bone_rotation.to_euler(sc.SBR_Props.rotation_mode)
                sbr_box_column.label(text="X: " + trunc(math.degrees(bone_rotation.x)) + "°")
                sbr_box_column.label(text="Y: " + trunc(math.degrees(bone_rotation.y)) + "°")
                sbr_box_column.label(text="Z: " + trunc(math.degrees(bone_rotation.z)) + "°")
        else:
            sbr_box_column.label(text=bpy.app.translations.pgettext("Need to select bone"))
    else:
        sbr_box_column.label(text=bpy.app.translations.pgettext("Need to enable bone edit mode"))
    sbr_column2 = layout.column(align=True)
    sbr_column2.prop(sc.SBR_Props, "world_space", text="")
    sbr_column2.prop(sc.SBR_Props, "rotation_mode", text="")
    sbr_column2.prop(sc.SBR_Props, "coordinate_system", text="")


def register():
    try:
        bpy.app.translations.register(__name__, translation_dict)
    except: pass
    bpy.utils.register_class(SBR_Props)
    bpy.utils.register_class(SBR_PT_panel)
    bpy.types.Scene.SBR_Props = bpy.props.PointerProperty(type=SBR_Props)


def unregister():
    try:
        bpy.app.translations.unregister(__name__)
    except: pass
    if hasattr(bpy.types.Scene, "SBR_Props") == True:
        del bpy.types.Scene.SBR_Props
    bpy.utils.unregister_class(SBR_PT_panel)
    bpy.utils.unregister_class(SBR_Props)


if __name__ == "__main__":
    register()
