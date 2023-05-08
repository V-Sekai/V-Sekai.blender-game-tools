import bpy
import bmesh

from enum import Enum
class TransformAction(Enum):
    Ignore = 1  # type: int
    Freeze = 2  # type: int
    Reset = 3   # type: int

class ArmatureGenerator(bpy.types.Operator):
    """Creates Skeletal Mesh from simulation - armature for every mesh object with root bone at the top of the hierarchy. Also duplicates source mesh objects with no simulation applied but skinned to bones."""
    bl_idname = "object.bake_simulation"
    bl_label = "Generate Armature"

    # Collections
    collection_main_name = 'Ossim'
    collection_skinned_name = 'Skinned Meshes'
    collection_output_name = 'Armature'

    collection_root = None
    collection_main = None
    collection_output = None
    collection_skinned = None

    def __init__(self):
        print("Armature generator initialized.")



    @classmethod
    def poll(cls, context):
        return bpy.context.view_layer.objects.active is not None

    @classmethod
    def deselect(cls, context):
        bpy.ops.object.select_all(action='DESELECT')
        context.scene.objects.active = None

    @classmethod
    def generate_bone_per_vertex(cls, context, of_object: object):
        print("\nGenerating bone per vertex for object %s." % of_object.name)

        armatures = []

        for vertex in of_object.data.vertices:
            vertex_location = of_object.matrix_world @ vertex.co
            bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
            bpy.ops.armature.select_all(action='TOGGLE')
            print("Translating to %s" % vertex_location)
            bpy.ops.transform.translate(value=vertex_location)
            bpy.ops.object.mode_set(mode='OBJECT')

            armature_master = context.view_layer.objects.active
            armature_master.parent = of_object
            armature_master.parent_type = 'VERTEX'

            # only pass on the index, not the vertex object
            armature_master.parent_vertices[0] = vertex.index

            armatures.append(armature_master)

        print("Created %s individual bones." % len(armatures))

        return armatures

    @classmethod
    def generate_union_armature(cls, context, armatures: [], name: str, collection_container):

        print("\nGenerating union armature with constraints for %s bones." % len(armatures))

        created_armatures = []

        for index, arm in enumerate(armatures):
            arm.select_set(state=False)

            world_translation = arm.matrix_world.to_translation()

            bpy.ops.object.armature_add(enter_editmode=True, location=world_translation)
            bpy.ops.armature.select_all(action='TOGGLE')
            bpy.ops.transform.translate(value=world_translation)
            bpy.ops.object.mode_set(mode='OBJECT')
            armature_slave = context.view_layer.objects.active
            created_armatures.append(armature_slave)

            index_prefix = ""
            if index + 1 < 10:
                index_prefix = "00"
            if 100 > index + 1 >= 10:
                index_prefix = "0"
            arm.name = "Ossim_Bone_" + name + "_" + index_prefix + str(index + 1)

            print("     New bone %s with world translation: %s" % (armature_slave.name, world_translation))

            bpy.ops.object.posemode_toggle()
            bpy.ops.pose.constraint_add(type='COPY_LOCATION')
            context.view_layer.objects.active.pose.bones[0].constraints["Copy Location"].target = arm
            bpy.ops.object.posemode_toggle()

            collection_container.objects.link(arm)  # add to scene
            arm.hide_viewport = True

        print("Created armature with %s bones. \n" % len(created_armatures))

        for arm in created_armatures:
            arm.select_set(state=True)
            bpy.ops.object.join()
        merged_arms = bpy.context.view_layer.objects.active

        return merged_arms

    @classmethod
    def bind_geometry(cls, bind_object : object, armature : object):
        print("Binding %s to armature %s." % (bind_object.name, armature.name))
        #bpy.ops.mesh.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = bind_object
        bpy.context.view_layer.objects.active = armature
        bind_object.select_set(state=True)
        armature.select_set(state=True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        if bpy.context.scene.parent_type == 'OBJECT':
            bpy.ops.object.parent_type = 'OBJECT'
        elif bpy.context.scene.parent_type == 'ARMATURE':
            bpy.ops.object.parent_type = 'ARMATURE'

    @classmethod
    def reduce_geometry(cls, context, reduce_target_object):
        print("Reducing geometry for %s." % reduce_target_object.name)
        context.view_layer.objects.active = reduce_target_object

        # This is an Object with a Mesh, see if it has the supported group name
        found = False
        reduce_group_name = bpy.context.scene.vgr
        for i in range(0, len(reduce_target_object.vertex_groups)):
            group = reduce_target_object.vertex_groups[i]
            if group.name == reduce_group_name:
                found = True

        # Selecting group (or all) vertices.

        context.view_layer.objects.active.editmode_toggle()
        bpy.ops.object.mode_set(mode='EDIT')
        return
        if found:
            cls.select_vertices(context.active_object, reduce_group_name)
            bpy.ops.mesh.select_all(action='INVERT')
        else:
            bpy.ops.mesh.select_all()

        bpy.ops.mesh.unsubdivide(iterations=context.scene.bone_vertex_frequency_decrease)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

    @classmethod
    def clean_object(cls, clean_object):
        if not clean_object.modifiers:
            return
        clean_object.modifiers.remove(clean_object.modifiers.get("Cloth"))

    @classmethod
    def duplicate_object(cls, linked, collection_container, source_object: object, action: object = TransformAction.Ignore) -> object:
        print("Duplicating object %s." % source_object.name)

        duplicated_object = source_object.copy()  # duplicate linked

        if not linked:
            duplicated_object.data = source_object.data.copy()  # optional: make this a real duplicate (not linked)

        # @Todo, @Incomplete: Reintroduce this using 2.8 API
        #bpy.context.scene.objects.link(duplicated_object)  # add to scene
        #bpy.context.view_layer.objects.link(duplicated_object)

        collection_container.objects.link(duplicated_object)

        print(duplicated_object.name)
        cls.clean_object(duplicated_object)
        if action == TransformAction.Reset:
            print("Duplicate Transform Action: Reset.")
            duplicated_object.location = (0, 0, 0)
            duplicated_object.rotation_euler = (0, 0, 0)
            duplicated_object.scale[0] = 1
            duplicated_object.scale[1] = 1
            duplicated_object.scale[2] = 1
        elif action == TransformAction.Freeze:
            print("Duplicate Transform Action: Freeze.")

        return duplicated_object

    @classmethod
    def select_vertices(cls, of_object, group_name):
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = of_object.data
        bm = bmesh.from_edit_mesh(mesh)

        # This is an Object with a Mesh, see if it has the supported group name
        group_index = -1
        for i in range(0, len(of_object.vertex_groups)):
            group = of_object.vertex_groups[i]
            if group.name == group_name:
                group_index = i

        print("Checking %s for assigned vertices." % of_object.name)

        indices = []

        # Now access the vertices that are assigned to this group
        for v in mesh.vertices:
            for vertGroup in v.groups:
                if vertGroup.group == group_index:
                    indices.append(v.index)
                    #print("Vertex %d is part of group." % v.index)

        vertices = [e for e in bm.verts]

        for vert in vertices:
            if vert.index in indices:
                vert.select = True
            else:
                vert.select = False

        bmesh.update_edit_mesh(mesh, True)
        bpy.ops.object.mode_set(mode='EDIT')

    def generateCloth(self, context):


        if bpy.context.scene.collection.children.get(self.collection_main_name) is None:
            bpy.context.scene.collection.children.link(self.collection_main)

        if self.collection_main.children.get(self.collection_skinned_name) is None:
            self.collection_main.children.link(self.collection_skinned)
        if self.collection_main.children.get(self.collection_output_name) is None:
            self.collection_main.children.link(self.collection_output)

        is_optimization_active = context.scene.bone_vertex_frequency_decrease > 1

        cloth_geometry_object = bpy.context.view_layer.objects.active

        print("--- Individual bones creation ---")

        # Generate bone per vertex.
        armatures = self.generate_bone_per_vertex(context, cloth_geometry_object)

        print ("--- Generating union armature ---")

        # Generate union armature A with constraints.
        merged_armature = self.generate_union_armature(context, armatures, cloth_geometry_object.name, self.collection_skinned)


        #merged_armature.name = "Ossim_Cloth_Mesh_With_Armature_" + cloth_geometry_object.name
        merged_armature.name = context.scene.armature_name + "_(" + cloth_geometry_object.name + ")"

        # Duplicate geometry to skin it, bind to armature.
        print("Duplicate cloth geometry to skin it, bind to armature.")
        duplicated_cloth_geometry = self.duplicate_object(False, self.collection_main, cloth_geometry_object, TransformAction.Freeze)  # type: object
        print("-- duplicated geometry : " + duplicated_cloth_geometry.name)
        #duplicated_cloth_geometry.name = "Ossim_Cloth_Rigged_Geometry_" + cloth_geometry_object.name
        duplicated_cloth_geometry.name = context.scene.skin_name

        # Move to Skin collection.
        self.collection_skinned = self.find_collection("Output")
        #if self.collection_skinned.objects.get(duplicated_cloth_geometry.name) is None:
        self.collection_skinned.objects.link(duplicated_cloth_geometry)

        self.bind_geometry(duplicated_cloth_geometry, merged_armature)

        cloth_geometry_object.name = context.scene.source_name

        # Parent bones to root.
        print("Parent bones to root.")
        bpy.ops.object.editmode_toggle()

        for bone in context.visible_bones:
            bone.parent = context.object.data.edit_bones[0]

        bpy.ops.object.editmode_toggle()

        self.collection_skinned.hide_render = False
        self.collection_skinned.hide_select = False
        self.collection_skinned.hide_viewport = False

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = duplicated_cloth_geometry
        duplicated_cloth_geometry.select_set(state=True)


    def does_have_vertex_group(self, object, group_name):
        for i in range(0, len(object.vertex_groups)):
            group = object.vertex_groups[i]
            if group.name == group_name:
                return True

    @staticmethod
    def find_collection(collection_name: str):
        if bpy.data.collections.get(collection_name) is None:
            return bpy.data.collections.new(collection_name)
        return bpy.data.collections.get(collection_name)

    def generateRigidbody(self, context):
        armatures = []
        skinned_objects = []
        root = None
        rootname = None

        if bpy.context.scene.collection.children.get(self.collection_main_name) is None:
            bpy.context.scene.collection.children.link(self.collection_main)

        if self.collection_main.children.get(self.collection_skinned_name) is None:
            self.collection_main.children.link(self.collection_skinned)
        if self.collection_main.children.get(self.collection_output_name) is None:
            self.collection_main.children.link(self.collection_output)


        self.collection_skinned.hide_render = False
        self.collection_skinned.hide_select = False
        self.collection_skinned.hide_viewport = False

        print("-----------------------------------")
        print("Bake simulation to armature started.")
        print("Filtering selected objects.")

        # First, filter mesh objects.
        for obj in context.selected_objects:
            obj_type = getattr(obj, 'type', '')
            if obj_type == 'MESH':
                print("Object to bake: " + obj.name)
            else:
                print("Object is not mesh, deselecting: " + obj.name)
                obj.select_set(state=False)

        # @Robustness: encapsulate chunks of code into
        # separate routines or even classes.

        # def AttachArmatures()
        for index, obj in enumerate(context.selected_objects):

            print("-------------------" + obj.name + "-------------------")
            bone_name = context.scene.bone_name + "_" + str(index)

            # Duplicate geometry to skin it.
            skin_object = obj.copy()  # duplicate linked

            if not context.scene.link_object:
                skin_object.data = obj.data.copy()  # optional: make this a real duplicate (not linked)
            #context.scene.objects.link(skin_object)  # add to scene
            self.collection_skinned.objects.link(skin_object)  # add to scene

            skin_object.location = (0, 0, 0)
            skin_object.rotation_euler = (0, 0, 0)
            skin_object.scale[0] = 1
            skin_object.scale[1] = 1
            skin_object.scale[2] = 1
            skin_object.select_set(state=True)
            context.view_layer.objects.active = skin_object

            if skin_object.rigid_body:
                bpy.ops.rigidbody.object_remove()
            if skin_object.animation_data:
                context.object.animation_data_clear()

            skin_object.name = context.scene.skin_name + "_" + str(index)

            print("Duplicated Source Mesh, New duplicated object name is: " + skin_object.name)
            skinned_objects.append(skin_object)
            context.view_layer.objects.active = obj

            # Creating armature.
            armature = bpy.ops.object.armature_add(enter_editmode=False, location=(0, 0, 0))
            armature_object = context.active_object
            if self.collection_output.objects.get(armature_object.name) is None:
                self.collection_output.objects.link(armature_object)
            if bpy.context.scene.collection.get(armature_object.name) is not None:
                bpy.context.scene.collection.objects.unlink(armature_object)

            # Assigning copy transform to new armature bone.
            bpy.ops.object.posemode_toggle()  # Enter pose mode.


            constraint = bpy.ops.pose.constraint_add(type='CHILD_OF')
            print("--- adding child constraint... " + str(armature_object.pose.bones[0].constraints[0].type))
            armature_object.pose.bones[0].constraints[0].target = obj
            print("--- adding constraint target: " + obj.name)
            #bpy.context.object.pose.bones["Bone"].constraints["Child Of"].target = bpy.data.objects["BakeSimArmature"]
            armature_object.pose.bones[0].name = bone_name
            #print("-- Assigning child constraint [{name}] to bone [{child}] : [{parent}]".format(name = constraint.name, child = armature_object.pose.bones[0].name, parent = bone_name))

            # Blender 2.91 fix.
            if bpy.app.version >= (2, 91, 0):
                print("blender 2.91 fix.")
                bpy.ops.constraint.childof_set_inverse(constraint="Child Of", owner='BONE')
                bpy.ops.constraint.childof_clear_inverse(constraint="Child Of", owner='BONE')

            bpy.ops.object.posemode_toggle()  # Leave pose mode.

            armatures.append(armature_object)
            armature_object.name = context.scene.bone_name + "_" + str(index)
            obj.name = context.scene.source_name + "_" + str(index)

            print("Index: " + str(index) + "    , object is: " + obj.name)
            print("Created armature named:" + armature_object.name + " with bone copying: " + obj.name)

            # Skin duplicated geo to bone.
            skin_object.select_set(state=True)
            context.view_layer.objects.active = skin_object
            if context.scene.clear_location:
                bpy.ops.object.location_clear(clear_delta=False)
            if context.scene.clear_rotation:
                bpy.ops.object.rotation_clear(clear_delta=False)
            if context.scene.clear_scale:
                bpy.ops.object.scale_clear(clear_delta=False)


            armature_object.select_set(state=True)
            context.view_layer.objects.active = armature_object
            #skin_object.parent_set(type='ARMATURE_NAME')
            bpy.ops.object.parent_set(type='ARMATURE_NAME')
            vertex_group = skin_object.vertex_groups[bone_name]

            # Set parent (armature) type to ARMATURE instead ob default
            # OBJECT type. Must be invoked after parenting to armature!
            context.view_layer.objects.active = skin_object
            if context.scene.parent_type == 'OBJECT':
                skin_object.parent_type = 'OBJECT'
            elif context.scene.parent_type == 'ARMATURE':
                skin_object.parent_type = 'ARMATURE'

            # Remove constraints if there are any.
            bpy.ops.object.constraints_clear()


            context.view_layer.objects.active = obj
            mesh = skin_object.data
            for vert in mesh.vertices:
                vertex_group.add([vert.index], 1.0, "ADD")

            #context.view_layer.objects.active.pose.bones[0].constraints["Copy Location"].target = arm

            # Return selection to armature
            # print("End of iteration")
            # print("Object names:")
            # print("           " + " obj name: " + obj.name + ", Type: " + obj.type)
            # print("           " + " skin_object name: " + skin_object.name + ", Type: " + obj.type)
            # print("           " + " armature_object name: " + armature_object.name + ", Type: " + obj.type)
            # print("")
            #print(
            #    "Active object: " + context.scene.objects.active.name + ", Type: " + context.scene.objects.active.type)

        # if len(armatures) > 0:
        #     end = ""
        #     if len(armatures) > 1:
        #         end = "s"
        #     print("Created " + str(len(armatures)) + " bone" + end + ":")



        if len(armatures) > 1:
            for arm in armatures:
                arm.select_set(state=True)
                context.view_layer.objects.active = arm
            bpy.ops.object.join()
        merged_arms = context.active_object



        # Create root bone:
        armature = bpy.ops.object.armature_add(enter_editmode=False, location=(0, 0, 0))
        root_object = context.active_object

        if self.collection_output.objects.get(root_object.name) is None:
            self.collection_output.objects.link(root_object)
        root_object.name = context.scene.armature_name
        bpy.ops.object.posemode_toggle()
  #      root_object.pose.bones[0].name = context.scene.root_name
  #      rootname = context.object.pose.bones[0].name
        rootname = "TT"
        bpy.ops.object.posemode_toggle()
        print("Root bone created: " + root_object.name)

        # Deselect all bones.
        bpy.ops.object.editmode_toggle()
        bpy.ops.armature.select_all(action='TOGGLE')
        bpy.ops.object.editmode_toggle()

        # Merge armatures and root bone.
        print("Merging armatures and root bone...")
        merged_arms.select_set(state=True)
        root_object.select_set(state=True)
        context.view_layer.objects.active = root_object
        bpy.ops.object.join()

        # Parent bones to root.
        print("Parent bones to root...")
        bpy.ops.object.editmode_toggle()

        for bone in context.visible_bones:
            bone.parent = context.active_object.data.edit_bones[0]

        bpy.ops.object.editmode_toggle()

        # Create layers vector with only one layer enabled.
        def layers(l):
            all = [False] * 20
            all[l] = True
            return all

        for skin in skinned_objects:
            skin.modifiers["Armature"].object = root_object

        #collection_skinned.hide_render = True
        #collection_skinned.hide_select = True
        #collection_skinned.hide_viewport = True

    def execute(self, context):

        self.collection_root = bpy.context.scene.collection
        self.collection_main = self.find_collection(self.collection_main_name)
        self.collection_output = self.find_collection(self.collection_output_name)
        self.collection_skinned = self.find_collection(self.collection_skinned_name)
        if context.scene.object_type == 'Rigidbody':
            self.generateRigidbody(context)
        elif context.scene.object_type == 'Cloth':
            self.generateCloth(context)


        return {'FINISHED'}


def register():
    bpy.utils.register_class(ArmatureGenerator)
    print("Registered armature generator operator.")


def unregister():
    bpy.utils.unregister_class(ArmatureGenerator)
    print("Unregistered armature generator operator.")
