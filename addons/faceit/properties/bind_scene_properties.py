import bpy
from bpy.types import Scene, Object, Bone
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------


# --------------- REGISTER/UNREGISTER --------------------
# |
# --------------------------------------------------------

def is_armature_poll(self, obj):
    scene = bpy.context.scene
    if obj.type == 'ARMATURE' and obj.name in scene.objects:
        if obj != scene.faceit_armature:
            return True


def register():

    Scene.faceit_body_armature = PointerProperty(
        name='Body Armature',
        type=Object,
        poll=is_armature_poll,
    )

    Scene.faceit_body_armature_head_bone = StringProperty(
        name='Bone',
        default='',
    )

    Scene.faceit_weights_restorable = BoolProperty(
        default=False,
    )
    Scene.faceit_expressions_restorable = BoolProperty(
        default=False,
    )
    Scene.faceit_corrective_sk_restorable = BoolProperty(
        default=False,
    )


def unregister():
    del Scene.faceit_weights_restorable
    del Scene.faceit_expressions_restorable
    del Scene.faceit_corrective_sk_restorable
