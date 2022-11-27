# MIT LICENSE
# Authored by iFire#6518 and alexfreyre#1663
# This code ONLY apply to a mesh and simulations with ONLY the same vertex number

import bpy

#Converts a MeshCache or Cloth modifiers to ShapeKeys
frame = bpy.context.scene.frame_start
for frame in range(bpy.context.scene.frame_end + 1):
    bpy.context.scene.frame_current = frame

    #for alembic files converted to MDD and loaded as MeshCache
    bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier="MeshCache")

    #for cloth simulations inside blender using a Cloth modifier
    #bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier="Cloth")

# loop through shapekeys and add as keyframe per frame
# https://blender.stackexchange.com/q/149045/87258
frame = bpy.context.scene.frame_start
for frame in range(bpy.context.scene.frame_end + 1):
    bpy.context.scene.frame_current = frame

    for shapekey in bpy.data.shape_keys:
        for i, keyblock in enumerate(shapekey.key_blocks):
            if keyblock.name != "Basis":
                curr = i - 1
                if curr != frame:
                    keyblock.value = 0
                    keyblock.keyframe_insert("value", frame=frame)
                else:
                    keyblock.value = 1
                    keyblock.keyframe_insert("value", frame=frame)

# bpy.ops.object.modifier_remove(modifier="MeshCache")
# bpy.ops.object.modifier_remove(modifier="Cloth")