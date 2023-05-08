import bpy

class CleanupOssimCollection(bpy.types.Operator):
    bl_idname = "ossim.cleanup_ossim_collection"
    bl_label = "Cleanup"
    bl_options = set()

    def clean_collection(self, collection_name):
        collection = bpy.data.collections.get(collection_name)
        if collection:
            print("Cleaning the collection: " + collection.name)

            while collection.objects:
                obj = collection.objects[0]
                collection.objects.unlink(obj)
                bpy.data.objects.remove(obj)

    def execute(self, context):

        self.clean_collection("Skinned")
        self.clean_collection("Output")

        return {'FINISHED'}

class PANEL1_PT_OssimMain(bpy.types.Panel):
    bl_idname = "ossim.generator_panel"
    bl_label = "Ossim"
    bl_space_type = 'VIEW_3D'

    bl_region_type = 'UI'
    bl_category = 'Ossim'


    def is_collection_cleanable(self, collection_name):
        collection = bpy.data.collections.get(collection_name)
        if collection:
            if len(collection.children) > 0 or len(collection.objects):
                return True
        return False

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        # Checking if user selected anything.
        if len(bpy.context.view_layer.objects.selected) <= 0:
            row = layout.row()
            row.label(text='Select something first.')

        if self.is_collection_cleanable("Skinned") or self.is_collection_cleanable("Output"):
            row = layout.row()
            row.operator("ossim.cleanup_ossim_collection")

        obj = bpy.context.view_layer.objects.active
        if obj:# and obj.select:
            obj_type = getattr(obj, 'type', '')
            if obj_type != 'ARMATURE':
                ##### Generate armature #####
                #### Generate button ####
                row = layout.row()
                row.scale_y = 1.5
                row_op_genarmature = row.operator("object.bake_simulation")

                ### Generator options ###
                box = layout.box()
                col = box.column()
                row = col.row()
                if scene.show_generator_options:
                    row.prop(scene, "show_generator_options", icon="TRIA_DOWN", text="", emboss=False)
                else:
                    row.prop(scene, "show_generator_options", icon="TRIA_RIGHT", text="", emboss=False)

                row.label(text='Generator options')
                col.prop(context.scene, 'object_type')
                #if context.scene.object_type == 'Cloth':
                    #col.prop(context.scene, 'bone_vertex_frequency_decrease')
                    #is_optimization_active = context.scene.bone_vertex_frequency_decrease > 1
                    # if is_optimization_active:
                    #     row = col.row()
                    #     row.label(text='Vertices to keep intact:')
                    #     row = col.row()
                    #     row.prop_search(bpy.context.scene, "vgr", context.active_object, "vertex_groups", text="Density")


                if scene.show_generator_options:
                    col.prop(context.scene, 'clear_location')
                    col.prop(context.scene, 'clear_rotation')
                    col.prop(context.scene, 'clear_scale')
                    col.prop(context.scene, 'parent_type')
                    col.prop(context.scene, "auto_cleanup_ossim_collection")
                    col.prop(context.scene, "link_object")
                    col.prop(scene, 'bone_name')
                    col.prop(scene, 'skin_name')
                    col.prop(scene, 'source_name')
                    col.prop(scene, 'root_name')
                    col.prop(scene, 'armature_name')

            elif obj_type == 'ARMATURE':
                ##### Autokeyframe #####
                #### Autokeyframe button ####
                row = layout.row()
                row.scale_y = 1.5
                row_op_autokeyframe = row.operator("object.auto_keyframe")

                row = layout.row()
                row.scale_y = 1.0
                row_op_clear_keyframes = row.operator("object.clear_keyframes")

                ### Autokeyframe options ###
                box = layout.box()
                col = box.column()
                row = col.row()
                if scene.show_autokeyframe_options:
                    row.prop(scene, "show_autokeyframe_options", icon="TRIA_DOWN", text="", emboss=False)
                else:
                    row.prop(scene, "show_autokeyframe_options", icon="TRIA_RIGHT", text="", emboss=False)

                row.label(text='Autokeyframing options')
                if scene.show_autokeyframe_options:
                    row = col.row()
                    col = row.column(align=True)
                    col.prop(context.scene, "keyframe_frequency")
                    col.prop(scene, 'frame_start', text='Start Frame')
                    col.prop(scene, 'frame_end', text='End Frame')
                    col.prop(context.scene, 'keyframe_type')

def register():
    initSceneProperties()

    for cls in (PANEL1_PT_OssimMain, CleanupOssimCollection):
        bpy.utils.register_class(cls)

    bpy.types.Scene.show_generator_options = bpy.props.BoolProperty(name='Show generator options', default=False)
    bpy.types.Scene.show_autokeyframe_options = bpy.props.BoolProperty(name='Show autokeyframe options', default=False)
    bpy.types.Scene.vgr = bpy.props.StringProperty(name="vertex_group_density")
    bpy.types.Scene.auto_cleanup_ossim_collection = bpy.props.BoolProperty(name='Auto cleanup Ossim collection', default=True)
    bpy.types.Scene.clear_location = bpy.props.BoolProperty(name='Clear Location', default=True)
    bpy.types.Scene.clear_rotation = bpy.props.BoolProperty(name='Clear Rotation', default=True)
    bpy.types.Scene.clear_scale = bpy.props.BoolProperty(name='Clear Scale', default=True)

def initSceneProperties():
    bpy.types.Scene.armature_name = bpy.props.StringProperty \
      (
        name = "Armature name",
        description = "Armature object name.",
        default = "BakeSimArmature"
      )
    bpy.types.Scene.bone_name = bpy.props.StringProperty \
      (
        name = "Bone name",
        description = "Prefix of the bone names.",
        default = "BakeSimBone"
      )
    bpy.types.Scene.skin_name = bpy.props.StringProperty \
      (
        name = "Skin name",
        description = "Prefix of the source mesh object"
      )
    bpy.types.Scene.source_name = bpy.props.StringProperty \
      (
        name = "Source Mesh name",
        description = "Prefix of the source mesh object names.",
        default = "BakeSimSource"
      )
    bpy.types.Scene.root_name = bpy.props.StringProperty \
      (
        name = "Root bone name",
        description = "Prefix of the root bone name.",
        default = "BakeSimRoot"
      )


    bpy.types.Scene.keyframe_frequency = bpy.props.IntProperty \
      (
        name = "Frequency",
        description = "How frequent autokeyframes will be placed.",
        default = 5,
        min = 1,
        max = 60
      )

    # Cloth
    bpy.types.Scene.object_type = bpy.props.EnumProperty \
            (
            name="Object type",
            description="",
            items=[
                ("Rigidbody", "Rigidbody", "Object uses rigidbody physics."),
                ("Cloth", "Cloth", "Generate bones for vertices of the cloth.")
            ]
        )
    bpy.types.Scene.bone_vertex_frequency_decrease = bpy.props.IntProperty \
            (
            name="Bone-Vertex Frequency Decrease",
            description="How times less frequent to place bones.",
            default=1,
            min=1,
            max=10
        )

    # Keyframes

    bpy.types.Scene.keyframe_type = bpy.props.EnumProperty \
            (
            name="Keyframe type",
            description="What keyframe info type to write.",
            items=[
                ("LocationAndRotation", "Location and Rotation", "Write both Location and Rotation information."),
                ("Location", "Location Only", "Write only Location information."),
                ("Rotation", "Rotation Only", "Write only Rotation information.")
            ]
        )
    bpy.types.Scene.link_object = bpy.props.BoolProperty \
            (
            name="Link duplicated object",
            description="",
            default = True
        )
    bpy.types.Scene.auto_cleanup_ossim_collection = bpy.props.BoolProperty \
            (
            name="Auto cleanup Ossim collection",
            description="",
            default=True
        )

    bpy.types.Scene.parent_type = bpy.props.EnumProperty \
            (
            name="Parent type",
            description="Parent type of the armature object.",
            items=[
                ("ARMATURE", "ARMATURE", "ARMATURE"),
                ("OBJECT", "OBJECT", "OBJECT")
            ]

        )


def unregister():
    del bpy.types.Scene.show_generator_options
    del bpy.types.Scene.vgr
    del bpy.types.Scene.show_autokeyframe_options
    del bpy.types.Scene.auto_cleanup_ossim_collection
    del bpy.types.Scene.clear_location
    del bpy.types.Scene.clear_rotaion
    del bpy.types.Scene.clear_scale

    for cls in (PANEL1_PT_OssimMain, CleanupOssimCollection):
        bpy.utils.unregister_class(cls)
