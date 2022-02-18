bl_info = {
    "name" : "OMI Blender glTF",
    "author" : "OMI Group",
    "description" : "",
    "blender" : (2, 93, 1),
    "version" : (0, 0, 1),
    "location" : "",
    "warning" : "",
    "category" : "Import-Export"
}

def get_version_string():
    return str(bl_info['version'][0]) + '.' + str(bl_info['version'][1]) + '.' + str(bl_info['version'][2])

from .reload_package import reload_package
if "bpy" in locals():
    reload_package(locals())

import bpy

from io_scene_gltf2.blender.imp.gltf2_blender_scene import BlenderScene
orig_create = BlenderScene.create
def dump(gltf, node):
    for n in [gltf.vnodes[i] for i in node.children]:
        print("dump", n, n.children)
        dump(gltf, n)

def patched_create(gltf):
    print("patched_create", loaded_extensions)
    hasEmitters = 'OMI_audio_emitter' in getattr(gltf.data, 'extensions_used', ())
    extensionData = gltf.data.extensions.get('OMI_audio_emitter', None)
    audioSources = extensionData['audioSources']
    audioEmitters = extensionData['audioEmitters']
    print("patched_create", audioSources[audioEmitters[0]['source']])
    inst = glTF2ImportUserExtension()
    orig_create(gltf)
    dump(gltf, gltf.vnodes[0])
    inst.import_gltf_hook(gltf, gltf.import_settings)
    root = gltf.vnodes['root']
    vnodes = [gltf.vnodes[i] for i in range(0, len(gltf.vnodes)-1)]
    for i, n in enumerate(vnodes):
        node = gltf.data.nodes[i]
        print("import descending...", i, node, n.blender_object)
        inst.import_node_hook(node, n.blender_object, gltf.import_settings)
BlenderScene.create = patched_create

#### monkey patching until io_scene_gltf2 2.93.1 support can be assumed
from io_scene_gltf2.blender.exp import gltf2_blender_export
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
orig_gather_gltf = gltf2_blender_export.__gather_gltf
def patched_gather_gltf(exporter, export_settings):
    orig_gather_gltf(exporter, export_settings)
    export_user_extensions('custom_gather_gltf_hook', export_settings, exporter._GlTF2Exporter__gltf)
    exporter._GlTF2Exporter__traverse(exporter._GlTF2Exporter__gltf.extensions)
gltf2_blender_export.__gather_gltf = patched_gather_gltf

from .extensions import queryExtensions, queryRegisterables, OMIExtension
loaded_extensions = []
registerables = []

class OMIExtensions(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(name="enabled", default=True)

def register():
    global registerables
    global loaded_extensions

    # detect whether Khronos io_scene_gltf2 is available
    if not hasattr(bpy.types, 'GLTF_PT_export_user_extensions'):
        raise "OMI Blender glTF depends on io_scene_gltf2"
    
    # register main panels
    registerables = queryRegisterables(globals())
    print("[OMI] register", registerables)
    OMIExtension.register_array(registerables)

    bpy.types.Scene.OMIExtensions = bpy.props.PointerProperty(type=OMIExtensions)

    # register extensions
    autodetected = queryExtensions()
    for Ext in autodetected:
        if hasattr(Ext, 'register'):
            Ext.register()
        else:
            print("Warning -- no .register found", Ext)
        instance = Ext()
        # print("[OMI]", instance.__module__)
        loaded_extensions.append(instance)
    print("[OMI] extensions:", [ext.__module__ for ext in loaded_extensions])
    # class tmp: extensions = {}
    # extensions[0].gather_gltf_hook(tmp(), {})

def unregister():
    global loaded_extensions
    global registerables

    del bpy.types.Scene.OMIExtensions

    print("[OMI] unregister bpy.types", registerables)
    OMIExtension.unregister_array(registerables) # unregister main panels below
    registerables = []

    print("[OMI] unregister extensions", registerables)
    for extension in loaded_extensions:
        if hasattr(extension.__class__, 'unregister'):
            if True: #try:
                extension.__class__.unregister()
            #except Exception as e:
            #    print("unregister error", extension.__class__, e)
        else:
            print("Warning -- no .unregister found", extension.__class__)
    loaded_extensions = []

class glTF2ImportUserExtension:
    def __init__(self):
        print("glTF2ImportUserExtension")

    def import_gltf_hook(self, root, import_settings):
        for extension in loaded_extensions:
            extension.import_gltf_hook(root, import_settings)

    def import_node_hook(self, node, blender_object, import_settings):
        for extension in loaded_extensions:
            extension.import_node_hook(node, blender_object, import_settings)
    
class glTF2ExportUserExtension:
    def __init__(self):
        print("glTF2ExportUserExtension")

    def gather_scene_hook(self, scene, blender_scene, export_settings):
        # NOTE: Currently this forwards the blender scene node back into our gltf node handler
        print("gather_scene_hook", scene.extensions)
        self.gather_node_hook(scene, blender_scene, export_settings)

    def gather_gltf_hook(self, export_settings, plan):
        print('[glTF2ExportUserExtension] gather_gltf_hook', export_settings, plan)

    def custom_gather_gltf_hook(self, root, export_settings):
        if root.asset.extras is None:
            root.asset.extras = {}
        root.asset.extras["OMI_Blender_GLTF_Version"] = get_version_string()
        print('[glTF2ExportUserExtension] custom_gather_gltf_hook', root)
        try:
            print('xxextensions', root.extensions)
            for extension in loaded_extensions:
                try:
                    extension.gather_gltf_hook(root, export_settings)
                except Exception as e:
                    print("glTF2ExportUserExtension custom_gather_gltf_hook error", extension, e)
                
        except Exception as e:
            print("glTF2ExportUserExtension error", e)

    def gather_asset_hook(self, asset, export_settings):
        print('[glTF2ExportUserExtension] gather_asset_hook', asset)
        for extension in loaded_extensions:
            try:
                extension.gather_asset_hook(asset, export_settings)
            except Exception as e:
                print("[glTF2ExportUserExtension] gather_asset_hook error", extension, e)

    def gather_node_hook(self, node, blender_object, export_settings):
        print('[glTF2ExportUserExtension] gather_node_hook', node)
        for extension in loaded_extensions:
            try:
                extension.gather_node_hook(node, blender_object, export_settings)
            except Exception as e:
                print("[glTF2ExportUserExtension] gather_node_hook error", extension, e)
            

class OMIObjectExtensions(bpy.types.Panel):
    bl_label = 'OMI Extensions'
    bl_idname = "NODE_PT_omi_extensions"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    def draw(self, context):
        pass # self.layout.label(text="OMIObjectPanel")

class OMISceneExtensions(bpy.types.Panel):
    bl_label = 'OMI Extensions'
    bl_idname = "NODE_PT_omi_scene_extensions"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'
    def draw(self, context):
        pass

### GLTF Export Screen
bpy.types.GLTF_PT_export_user_extensions.bl_id = 'GLTF_PT_export_user_extensions'
class OMIGLTF_PT_export_user_extensions(bpy.types.Panel):
    bl_id = 'OMIGLTF_PT_export_user_extensions'
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "OMI Extensions"
    bl_parent_id = "FILE_PT_operator"
    # FIXME: iFire 2022-02-17 Reported did not work with testing.
    # bl_parent_id = "GLTF_PT_export_user_extensions"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        OMIGLTF_PT_export_user_extensions.bl_parent_id = "x"
        print("OMIGLTF_PT_export_user_extensions", operator.bl_idname, OMIGLTF_PT_export_user_extensions.bl_parent_id)
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        props = context.scene.OMIExtensions
        self.layout.prop(props, 'enabled', text="")

    def draw(self, context):
        self.layout.label(text="test")
        pass

