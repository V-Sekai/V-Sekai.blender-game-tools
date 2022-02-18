from . import OMIExtension

ID = "OMI_physics"
class OMIPhysicsExtension(OMIExtension):
    def gather_gltf_hook(self, root, export_settings):
        print("[OMIPhysicsExtension] gather_gltf_hook", ID, root)
        return
        root.extensions[ID] = OMIExtension.Extension(
            name=ID,
            extension={"test": 1},
            required=False
        )

    def gather_node_hook(self, node, blender_object, export_settings):
        return
        node.extensions = getattr(node, 'extensions', {})
        node.extensions[ID] = { "physicsEmitter": 123}