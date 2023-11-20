# -*- coding: utf-8 -*-

import bpy

from . import bone, camera, material, rigid_body, root

__properties = {
    bpy.types.Object: {
        'mmd_type': bpy.props.EnumProperty(
            name='Type',
            description='Internal MMD type of this object (DO NOT CHANGE IT DIRECTLY)',
            default='NONE',
            items=[
                ('NONE', 'None', '', 1),
                ('ROOT', 'Root', '', 2),
                ('RIGID_GRP_OBJ', 'Rigid Body Grp Empty', '', 3),
                ('JOINT_GRP_OBJ', 'Joint Grp Empty', '', 4),
                ('TEMPORARY_GRP_OBJ', 'Temporary Grp Empty', '', 5),
                ('PLACEHOLDER', 'Place Holder', '', 6),

                ('CAMERA', 'Camera', '', 21),
                ('JOINT', 'Joint', '', 22),
                ('RIGID_BODY', 'Rigid body', '', 23),
                ('LIGHT', 'Light', '', 24),

                ('TRACK_TARGET', 'Track Target', '', 51),
                ('NON_COLLISION_CONSTRAINT', 'Non Collision Constraint', '', 52),
                ('SPRING_CONSTRAINT', 'Spring Constraint', '', 53),
                ('SPRING_GOAL', 'Spring Goal', '', 54),
            ]
        ),
        'mmd_root': bpy.props.PointerProperty(type=root.MMDRoot),
        'mmd_camera': bpy.props.PointerProperty(type=camera.MMDCamera),
        'mmd_rigid': bpy.props.PointerProperty(type=rigid_body.MMDRigidBody),
        'mmd_joint': bpy.props.PointerProperty(type=rigid_body.MMDJoint),
    },
    bpy.types.Material: {
        'mmd_material': bpy.props.PointerProperty(type=material.MMDMaterial),
    },
    bpy.types.PoseBone: {
        'mmd_bone': bpy.props.PointerProperty(type=bone.MMDBone),
        'is_mmd_shadow_bone': bpy.props.BoolProperty(name='is_mmd_shadow_bone', default=False),
        'mmd_shadow_bone_type': bpy.props.StringProperty(name='mmd_shadow_bone_type'),
        'mmd_ik_toggle': bone._MMDPoseBoneProp.mmd_ik_toggle,
    }
}


def __set_hide(prop, value):
    prop.hide_set(value)
    if getattr(prop, 'hide_viewport'):
        setattr(prop, 'hide_viewport', False)


def __patch(properties):  # temporary patching, should be removed in the future
    prop_obj = properties.setdefault(bpy.types.Object, {})

    prop_obj['select'] = bpy.props.BoolProperty(
        get=lambda prop: prop.select_get(),
        set=lambda prop, value: prop.select_set(value),
        options={'SKIP_SAVE', 'ANIMATABLE', 'LIBRARY_EDITABLE', },
    )
    prop_obj['hide'] = bpy.props.BoolProperty(
        get=lambda prop: prop.hide_get(),
        set=__set_hide,
        options={'SKIP_SAVE', 'ANIMATABLE', 'LIBRARY_EDITABLE', },
    )


if bpy.app.version >= (2, 80, 0):
    __patch(__properties)


def register():
    for typ, t in __properties.items():
        for attr, prop in t.items():
            if hasattr(typ, attr):
                print(' * warning: overwrite ', typ, attr)
            setattr(typ, attr, prop)


def unregister():
    for typ, t in __properties.items():
        for attr in t.keys():
            if hasattr(typ, attr):
                delattr(typ, attr)
