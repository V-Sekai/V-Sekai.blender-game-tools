import bpy


def insert_keyframe(context, index):
    context.scene.frame_set(index)
    if context.scene.keyframe_type == 'Location':
        bpy.ops.anim.keyframe_insert_menu(type='Location')
    elif context.scene.keyframe_type == 'Rotation':
        bpy.ops.anim.keyframe_insert_menu(type='Rotation')
    else:
        bpy.ops.anim.keyframe_insert_menu(type='Location')
        bpy.ops.anim.keyframe_insert_menu(type='Rotation')
    print("Inserting keyframe [" + str(index) + "]  of type: " + str(context.scene.keyframe_type))


def delete_keyframe(context, index):
    context.scene.frame_set(index)
    bpy.ops.anim.keyframe_delete_v3d()


class ClearKeyframes(bpy.types.Operator):
    bl_idname = "object.clear_keyframes"
    bl_label = "Clear keyframes"

    def execute(self, context):
        print("Clearing keyframes...")
        bpy.ops.anim.keyframe_clear_v3d()
        return {'FINISHED'}


class AutoKeyframe(bpy.types.Operator):
    """Creates Skeletal Mesh from simulation - armature for every mesh object with root bone at the top of the hierarchy. Also duplicates source mesh objects with no simulation applied but skinned to bones."""
    bl_idname = "object.auto_keyframe"
    bl_label = "Auto keyframe armature"

    def __init__(self):
        print("Autokeyframe operation init.")

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):

        print("Autokeyframing started.")

        # Set timeline to the beginning.
        context.scene.frame_set(context.scene.frame_start)

        # Enter pose mode.
        bpy.ops.object.posemode_toggle(True)
        bpy.ops.pose.select_all(action='SELECT')

        number_of_frames = context.scene.frame_end - context.scene.frame_start
        print("Number of frames: " + str(number_of_frames))

        currentFrame = context.scene.frame_start
        while currentFrame < context.scene.frame_end:
            insert_keyframe(context, currentFrame)
            currentFrame += context.scene.keyframe_frequency
        insert_keyframe(context, context.scene.frame_end)

        # Exit pose mode.
        bpy.ops.object.posemode_toggle()
        context.scene.frame_set(context.scene.frame_start)

        print("Autokeyframing ended.")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(AutoKeyframe)
    bpy.utils.register_class(ClearKeyframes)
    print("Registered autokeyframe operator.")


def unregister():
    bpy.utils.unregister_class(AutoKeyframe)
    bpy.utils.unregister_class(ClearKeyframes)
    print("Unregistered autokeyframe operator.")
