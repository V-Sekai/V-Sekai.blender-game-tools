import bpy
from . import operators

align_normal_type_items = (('0', 'Use Face Normal', ''),
                                    ('1', 'Use Vertex Normals', ''),
                                     ('2', 'Use Custom Normal', ''))

approach_items = (('0', 'Use Faces', ''),
                                    ('1', 'Use Triangulated Faces', ''))

pattern_items = (('0', 'Checker', ''),
                                    ('1', 'Brick', ''))

obj_pos_items = (('0', 'On Top of Face', ''),
                                    ('1', 'In Middle of Face', ''),
                                    ('2', 'Below Face', ''))

def exec_interactive(self, context):
    if operators.main_tool_poll(context) and context.scene.mesh_mat_interactive_mode:
        bpy.ops.view3d.mesh_materializer('INVOKE_DEFAULT')

class MeshMaterializerSourceObject(bpy.types.PropertyGroup):
    """A class representing the properties of a source object for the mesh material."""
    name : bpy.props.StringProperty(name="Name", default="Unknown")
    is_enabled : bpy.props.BoolProperty(name="Enabled", default=True, update=exec_interactive)
    use_custom_parameters : bpy.props.BoolProperty(name="Customize", default=False, update=exec_interactive)
    randomize_parameters : bpy.props.BoolProperty(name="Randomize", default=False, update=exec_interactive)

    randomize_parameters_seed : bpy.props.IntProperty(
            name="Randomize Seed",
            description="Random Seed for object parameters",
            min=0,
            default=654321, 
            update=exec_interactive)

    location : bpy.props.FloatVectorProperty(name="Location", default=[0,0,0], precision=4, subtype='XYZ', update=exec_interactive)
    scale_x : bpy.props.FloatProperty(name="Scale X", default=1, min=0, precision=4, update=exec_interactive)
    scale_y : bpy.props.FloatProperty(name="Scale Y", default=1, min=0, precision=4, update=exec_interactive)
    scale_z : bpy.props.FloatProperty(name="Scale Z", default=1, min=0, precision=4, update=exec_interactive)
    rotate : bpy.props.FloatVectorProperty(name="Rotate", default=[0,0,0], precision=4, subtype="EULER", update=exec_interactive)
    maintain_proportions : bpy.props.BoolProperty(name="Maintain Aspect Ratio", default=False, update=exec_interactive)
    

    location_rand : bpy.props.FloatVectorProperty(name="Location", default=[0,0,0], precision=4, subtype='XYZ', update=exec_interactive)
    scale_x_rand : bpy.props.FloatProperty(name="+/-", default=0, min=0, precision=2, update=exec_interactive)
    scale_y_rand : bpy.props.FloatProperty(name="+/-", default=0, min=0, precision=2, update=exec_interactive)
    scale_z_rand : bpy.props.FloatProperty(name="+/-", default=0, min=0, precision=2, update=exec_interactive)
    rotate_rand : bpy.props.FloatVectorProperty(name="+/-", default=[0,0,0], precision=4, subtype="EULER", update=exec_interactive)

    align_normal : bpy.props.BoolProperty(name="Normal Alignment", default=True, update=exec_interactive)
    align_normal_type : bpy.props.EnumProperty(
                                items= align_normal_type_items,
                                name = "Normal alignment", default='1',
                                update=exec_interactive)
    normal_height : bpy.props.FloatProperty(name="Height", default=1.0, precision=4, update=exec_interactive)
    obj_pos : bpy.props.EnumProperty(
                                items= obj_pos_items,
                                name = "Position Object", default='0', 
                                update=exec_interactive)
    custom_normal : bpy.props.FloatVectorProperty(
            name="Custom Normal",
            description="Custom upwards direction of object",
            subtype='XYZ',
            default=[0,0,1],
            min=-1,
            max=1,
            step=1, 
            update=exec_interactive
            )


class MeshMaterializerGeneralProperty:
    """General Properties for Mesh Material Pattern."""
    def __init__(self,
                    across,
                    down,
                    randomize_parameters,
                    randomize_parameters_seed,
                    location,
                    scale_x,
                    scale_y,
                    scale_z,
                    rotate,
                    location_rand,
                    scale_x_rand,
                    scale_y_rand,
                    scale_z_rand,
                    rotate_rand,
                    maintain_proportions,
                    align_normal,
                    align_normal_type,
                    normal_height,
                    obj_pos,
                    custom_normal):
        self.across = across
        self.down = down
        self.randomize_parameters = randomize_parameters
        self.randomize_parameters_seed = randomize_parameters_seed
        self.location = location
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.scale_z = scale_z
        self.rotate = rotate
        self.location_rand = location_rand
        self.scale_x_rand = scale_x_rand
        self.scale_y_rand = scale_y_rand
        self.scale_z_rand = scale_z_rand
        self.maintain_proportions = maintain_proportions
        self.rotate_rand = rotate_rand
        self.align_normal = align_normal
        self.align_normal_type = align_normal_type
        self.normal_height = normal_height
        self.obj_pos = obj_pos
        self.custom_normal = custom_normal

class MeshMaterializerCustomProperty(MeshMaterializerGeneralProperty):
    """Source Object Specific Properties for Mesh Material Pattern."""
    def __init__(self,
                    name,
                    is_enabled,
                    use_custom_parameters,
                    randomize_parameters,
                    randomize_parameters_seed,
                    location,
                    scale_x,
                    scale_y,
                    scale_z,
                    rotate,
                    location_rand,
                    scale_x_rand,
                    scale_y_rand,
                    scale_z_rand,
                    rotate_rand,
                    maintain_proportions,
                    align_normal,
                    align_normal_type,
                    normal_height,
                    obj_pos,
                    custom_normal):

    
        self.name = name
        self.is_enabled = is_enabled
        self.use_custom_parameters = use_custom_parameters
        

        super().__init__(None,
                                None,
                                randomize_parameters,
                                randomize_parameters_seed,
                                location,
                                scale_x,
                                scale_y,
                                scale_z,
                                rotate,
                                location_rand,
                                scale_x_rand,
                                scale_y_rand,
                                scale_z_rand,
                                rotate_rand,
                                maintain_proportions,
                                align_normal,
                                align_normal_type,
                                normal_height,
                                obj_pos,
                                custom_normal)


class MeshMaterializerCustomObjectProperty(MeshMaterializerCustomProperty):
    """Customized Properties for Mesh Material Pattern creation."""
    def __init__(self,
                    meshMaterializerCustomProperty,
                    bm_cached):

        super().__init__(meshMaterializerCustomProperty.name,
                    meshMaterializerCustomProperty.is_enabled,
                    meshMaterializerCustomProperty.use_custom_parameters,
                    meshMaterializerCustomProperty.randomize_parameters,
                    meshMaterializerCustomProperty.randomize_parameters_seed,
                    meshMaterializerCustomProperty.location,
                    meshMaterializerCustomProperty.scale_x,
                    meshMaterializerCustomProperty.scale_y,
                    meshMaterializerCustomProperty.scale_z,
                    meshMaterializerCustomProperty.rotate,
                    meshMaterializerCustomProperty.location_rand,
                    meshMaterializerCustomProperty.scale_x_rand,
                    meshMaterializerCustomProperty.scale_y_rand,
                    meshMaterializerCustomProperty.scale_z_rand,
                    meshMaterializerCustomProperty.rotate_rand,
                    meshMaterializerCustomProperty.maintain_proportions,
                    meshMaterializerCustomProperty.align_normal,
                    meshMaterializerCustomProperty.align_normal_type,
                    meshMaterializerCustomProperty.normal_height,
                    meshMaterializerCustomProperty.obj_pos,
                    meshMaterializerCustomProperty.custom_normal)

        self.bm_cached = bm_cached