from . import OMIExtension, queryRegisterables
import bpy

from io_scene_gltf2.io.exp.gltf2_io_binary_data import BinaryData

ID = "OMI_audio_emitter"
VERSION = "X.X.X"

import json
from collections import namedtuple, OrderedDict

from ..omi_audio_utils import AudioPlayback
import os

class OMIAudioEmitterExtension(OMIExtension):

    class ExportData:
        """struct to keep track of incrementally prepared export data"""
        def __init__(self):
            self.audioSources = []
            self.audioEmitters = []
            self.sourcesByFilename = {}

    def __init__(self):
        super().__init__()
        self.export = OMIAudioEmitterExtension.ExportData()
        # FIXME: trying to mount properties like this currently throws an exception
        # self.properties = bpy.context.scene.OMIExtensions

    def _enabled(self):
        # FIXME: temporary workaround; would prefer to use self.properties.enabled
        return bpy.context.scene.OMIExtensions.enabled

    def _gather_node(self, blender_object):
        """append Object's audio information to the incremental export arrays"""
        p = getattr(blender_object, 'OMI_audio_pair', None)
        if not p: return
        if not p.source.filename:
            print("skipping pair w/o filename", p.source.name)
            return
        print("PROCESSING", p.source.name)

        ## audioSource
        # simple de-deduping -- identical filenames will reuse the source / index
        sourceIndex = self.export.sourcesByFilename.get(p.source.filename, None)
        if sourceIndex is None:
            sourceIndex = len(self.export.audioSources)
            self.export.sourcesByFilename[p.source.filename] = sourceIndex
            buffer = None
            if os.path.isfile(p.source.filename):
                with open(p.source.filename, 'rb') as f:
                    buffer = BinaryData(f.read())
            mimeType = p.source.mimeType
            if mimeType == "":
                mimeType = "audio/mpeg"
            self.export.audioSources.append({
                'name': p.source.name,
                'uri': p.source.filename,
                'bufferView': buffer,
                'mimeType': mimeType,
            })

        ## audioEmitter
        c = p.emitter
        emitterIndex = len(self.export.audioEmitters)
        self.export.audioEmitters.append({
            'type': c.type,
            'gain': c.gain,
            'loop': c.loop,
            'playing': c.playing,
            'source': sourceIndex,
            'coneInnerAngle': c.coneInnerAngle,
            'coneOuterAngle': c.coneOuterAngle,
            'coneOuterGain': c.coneOuterGain,
            'distanceModel': c.distanceModel,
            'maxDistance': c.maxDistance,
            'refDistance': c.refDistance,
            'rolloffFactor': c.rolloffFactor,

            'name': c.name,
        })
        return emitterIndex

    def gather_scene_hook(self, root, blender_scene, export_settings):
      print("GATHER_SCENE_HOOK", self)

    def gather_gltf_hook(self, root, export_settings):
      print("GATHER_GLTF_HOOK", self)
      if not self._enabled(): return
      print("[OMIAudioEmitterExtension] gather_gltf_hook", ID, root)
      try:
        if not root: return

        print("[OMIAudioEmitterExtension] gather_gltf_hook...", root.scenes[0].extensions)

        # https://github.com/omigroup/gltf-extensions/blob/OMI_audio_emitter/extensions/2.0/OMI_audio_emitter/schema/audioEmitter.schema.json#L7
        root.extensions[ID] = self.Extension(
            name = ID,
            extension = {
                'audioSources': self.export.audioSources,
                'audioEmitters': self.export.audioEmitters,
            },
            required = False
        )
      except Exception as e:
          print("EXCEPTION", e)
          import traceback
          traceback.print_exc()

    def gather_asset_hook(self, asset, export_settings):
        if not self._enabled(): return
        # TODO: incorporate add-on version somewhere
        # asset.extras = getattr(asset, 'extras', {}) or {}
        # asset.extras['OMI_audio_emitter'] = { 'version': VERSION }
        print("GATHER ASSET", asset.to_dict())

    def gather_node_hook(self, node, blender_object, export_settings):
        # print("[OMIAudioEmitterExtension] gather_node_hook", ID, node, blender_object.__class__ == bpy.types.Scene)

        # NOTE: this is one way to handle scene-level extensions
        if blender_object.__class__ == bpy.types.Scene:
            print("TODO: scene-level audio emitters", hasattr(blender_object, 'OMI_audio_pair'))
            return

        print("GATHER_NODE_HOOK", self, getattr(self, 'export', None))
        if not self._enabled(): return
        if not node: return
        emitterIndex = self._gather_node(blender_object)
        if emitterIndex is None:
            print("[OMIAudioEmitterExtension] ** ==== gather_node_hook -- skipping emitterIndex", emitterIndex)
            return

        node.extensions = getattr(node, 'extensions', {})
        print("[OMIAudioEmitterExtension] ** gather_node_hook", ID, self.Extension)

        node.extensions[ID] = self.Extension(
            name=ID,
            extension={
                'audioEmitter': emitterIndex
            },
            required=False
        )


    ######################### TODO: PROTOTYPE IMPORT SUPPORT #######
    def import_gltf_hook(self, root, import_settings):
        try:
            extensions = root.data.extensions[ID]
        except: return
        scene = bpy.context.scene
        self.audioSources = extensions.get('audioSources', [])
        self.audioEmitters = extensions.get('audioEmitters', [])
        print("[OMIAudioEmitterExtension] audio import_gltf_hook #sources#", len(self.audioSources))
        print("[OMIAudioEmitterExtension] audio import_gltf_hook #emitters#", len(self.audioEmitters))
        for node in root.data.scenes:
            extension = (node.extensions or {}).get(ID, {})

    def import_node_hook(self, node, blender_object, import_settings):
        extension = (node.extensions or {}).get(ID, {})
        scene = bpy.context.scene
        print("IMPORT SETTINGS", import_settings['filepath'])
        # audioEmitters = scene.xOMI_audio_emitters.value
        if 'audioEmitter' in extension:
            emitterData = self.audioEmitters[extension['audioEmitter']]
            sourceData = self.audioSources[emitterData['source']]
            print("[OMIAudioEmitterExtension] audio import_node_hook Adding emitter instance", extension, blender_object.OMI_audio_pair, sourceData, emitterData)

            source = blender_object.OMI_audio_pair.source
            source.name = sourceData['name']
            source.mimeType = sourceData.get('mimeType', '')
            if 'uri' in sourceData:
                source.filename = os.path.join(os.path.dirname(import_settings['filepath']), sourceData['uri'])
            else:
                source.filename = 'bufferView://' + str(sourceData.get('bufferView', None))
            
            emitter = blender_object.OMI_audio_pair.emitter
            for k in emitterData.keys():
                v = emitterData[k]
                if not hasattr(emitter, k):
                    print("[OMIAudioEmitterExtension] audio import_gltf_hook (unknown emitter.prop: ", k, v, ')')
                else:
                    annot = AudioEmitterProperties.__annotations__[k]
                    setattr(emitter, k, v)
                    print("[OMIAudioEmitterExtension] audio import_gltf_hook emitter.", k, '=', v, '==', getattr(emitter, k))
            # blender_object.OMI_audio_pair = self.audioPairs[extension['audioEmitter']]
            print("[OMIAudioEmitterExtension] audio import_node_hook", blender_object.OMI_audio_pair)
        pass


    @staticmethod
    def register():
        print("[OMIAudioEmitterExtension] OMI_audio_emitter::register")
        import os
        if os.environ.get("OMI_DEBUG", False): bpy.app.timers.register(omi_emitter_debug)

        OMIAudioEmitterExtension.registerables = queryRegisterables(globals())
        OMIExtension.register_array(OMIAudioEmitterExtension.registerables)

        # bpy.types.Scene.OMIAudioExtensionProperties = bpy.props.PointerProperty(type=OMIAudioExtensionProperties)

        # NOTE: old scene level plumbing
        # bpy.types.Scene.OMI_audio_pairs = bpy.props.CollectionProperty(type=AudioPair)
        
        # per-object audio emitter (... can "objects" have multiple emitters?)
        bpy.types.Object.OMI_audio_pair = bpy.props.PointerProperty(type=AudioPair)
        
    @staticmethod
    def unregister():
        print("[OMIAudioEmitterExtension] OMI_audio_emitter::unregister")
        OMIExtension.unregister_array(OMIAudioEmitterExtension.registerables)
        OMIAudioEmitterExtension.registerables = []
        del bpy.types.Object.OMI_audio_pair
        # del bpy.types.Scene.OMIAudioExtensionProperties
        #del bpy.types.Scene.OMI_audio_pairs

    # @staticmethod
    # def indexOfPair(context, pair):
    #     audioPairs = [c.OMI_audio_pair for c in bpy.data.objects if c.OMI_audio_pair is not None ]
    #     return audioPairs.index(pair)

    @staticmethod
    def gatherPairs(context):
        return [c.OMI_audio_pair for c in bpy.data.objects if c.OMI_audio_pair is not None ]

    @staticmethod
    def pairAt(context, index):
        audioPairs = [c.OMI_audio_pair for c in bpy.data.objects if c.OMI_audio_pair is not None ]
        return audioPairs[index]
        
OMIAudioEmitterExtension.registerables = []

class AudioSourceProperties(bpy.types.PropertyGroup):
    # index: bpy.props.IntProperty(name="index")
    name: bpy.props.StringProperty(name="name")
    mimeType: bpy.props.StringProperty(name="mimeType")
    filename: bpy.props.StringProperty(
        name="Audio File", description='Audio File', subtype='FILE_PATH'
    )

class AudioSourceArrayProperty(bpy.types.PropertyGroup):
    value: bpy.props.CollectionProperty(name="value", type=AudioSourceProperties)
    enabled: bpy.props.BoolProperty(name="enabled")

class ResetAudioPair(bpy.types.Operator):
    bl_idname = "wm.reset_audio_pair"
    bl_label = "Clear"
    target = None
    def execute(self, context):
        object = ResetAudioPair.target #findObjectByHash(context, self.object_path)
        pair = object.OMI_audio_pair
        pair.reset()
        return {'FINISHED'}

# .audioEmitter
class AudioEmitterProperties(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="name")
    type: bpy.props.EnumProperty(
        name='type', description='...', default='global',
        items={
            ('positional', 'positional', 'Positional...'),
            ('global', 'global', 'Global...'),
        }
    )
    gain: bpy.props.FloatProperty(name="Gain")
    loop: bpy.props.BoolProperty(name="Loop")
    playing: bpy.props.BoolProperty(name="Playing")
    coneInnerAngle: bpy.props.FloatProperty(name="coneInnerAngle", unit='ROTATION', subtype='ANGLE')
    coneOuterAngle: bpy.props.FloatProperty(name="coneOuterAngle", unit='ROTATION')
    coneOuterGain: bpy.props.FloatProperty(name="coneOuterGain")
    distanceModel: bpy.props.EnumProperty(
        name='distanceModel', description='...', default='inverse',
        items={
            ('linear', 'linear', 'A linear distance model calculating the gain induced by the distance according to: 1 - rolloffFactor * (distance - refDistance) / (maxDistance - refDistance)'),
            ('inverse', 'inverse', 'An inverse distance model calculating the gain induced by the distance according to: refDistance / (refDistance + rolloffFactor * (Math.max(distance, refDistance) - refDistance))'),
            ('exponential', 'exponential', 'An exponential distance model calculating the gain induced by the distance according to: pow((Math.max(distance, refDistance) / refDistance, -rolloffFactor)'),
        }
    )
    maxDistance: bpy.props.FloatProperty(name="maxDistance")
    refDistance: bpy.props.FloatProperty(name="refDistance")
    rolloffFactor: bpy.props.FloatProperty(name="rolloffFactor")


class AudioPair(bpy.types.PropertyGroup, AudioPlayback):
    source: bpy.props.PointerProperty(type=AudioSourceProperties)
    emitter: bpy.props.PointerProperty(type=AudioEmitterProperties)
    def reset(self):
        self.source.name = ''
        self.source.filename = ''
        self.stop()

class PreviewEmitter(bpy.types.Operator):
    bl_idname = "wm.omi_preview_emitter"
    bl_label = "Preview"
    # object_path: bpy.props.StringProperty(name="object_path")

    target = None
    def execute(self, context):
        object = PreviewEmitter.target #findObjectByHash(context, self.object_path)
        emitter = object.OMI_audio_pair.emitter
        clip = object.OMI_audio_pair.source #OMIAudioEmitterExtension.findClipByIndex(context, emitter.source)
        self.report({'INFO'}, str(self) + " TODO: Preview Emitter " + str(clip.filename if clip else clip) + "//"+str(clip))
        object.OMI_audio_pair.togglePlayback()
        return {'FINISHED'}

class ClipsOperator(bpy.types.Operator):
    bl_idname = "wm.omi_clips_operator"
    bl_label = "Clip"
    def item_cb(self, context):  
        clips = [( "-1", "", "")]
        for index, pair in OMIAudioEmitterExtension.gatherPairs(context):
            clips.append((str(index), pair.source.name, pair.source.filename))
        return clips
    clip:  bpy.props.EnumProperty(items=item_cb)
    target = None
    def execute(self, context): 
        index = int(self.clip)
        clip = OMIAudioEmitterExtension.pairAt(context, index)
        print("CLIPSOPERATOR", ClipsOperator.target, clip, index)
        emitter = ClipsOperator.target.OMI_audio_pair
        print(emitter, "EXECUTE", index, self.clip)
        emitter.source.name = clip.name
        emitter.source.filename = clip.filename
        self.report({'INFO'}, "OPERATOR: Select Clip " + str(clip.name if clip else None) +  "|" + str(emitter.source))
        return {"FINISHED"}  

# Object custom property panel

class ObjectEmitterPanel(bpy.types.Panel):
    bl_label = 'Audio Emitter'
    bl_idname = "NODE_PT_omi_object_audio_emitter"
    bl_parent_id = "NODE_PT_omi_extensions"
    bl_space_type = 'PROPERTIES'
    # bl_options = {'HIDE_HEADER'}
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    def draw(self, context):
        box = self.layout.box()
        # box.label(text="asdfasdf")
        self._draw(context, box, context.object)

    def _draw(self, context, layout, object):
        layout = layout.box()
        d = getattr(object, 'OMI_audio_pair', None)
        # print("ObjectEmitterPanel._draw", d.source, d.emitter)
        ClipsOperator.target = object
        row = layout.split(factor=0.75)
        # row.operator_menu_enum(ClipsOperator.bl_idname, "clip", text=d.source.name if d.source else "", icon="SCENE")
        #layout.label(text="index: " + str(emitter.source))
        row.prop(d.source, 'filename')
        row = row.split(factor=0.5)
        remove_operator = row.operator("wm.reset_audio_pair", icon="X", text="")
        ResetAudioPair.target = object
        if d.isPlaying():
            ico = "MESH_PLANE" # FIXME: is there a better "STOP" icon?
        else:
            ico = "PLAY"
        col = row.column()
        op = col.operator("wm.omi_preview_emitter", icon=ico, text="")
        col.enabled = os.path.exists(d.source.filename)
        PreviewEmitter.target = object
        # [layout.prop(d.source, n) for n in ['filename']] #'mimeType',
        if not d.source.filename: return
        [layout.prop(d.emitter, n) for n in [
            'name',
            'type',
            'gain', 'loop', 'playing',
            'coneInnerAngle', 'coneOuterAngle', 'coneOuterGain', 
            'distanceModel', 'maxDistance', 'refDistance', 'rolloffFactor']]

# # Scene custom property
# class SceneAudioSourcesPanel(bpy.types.Panel):
#     bl_label = 'Audio Clips'
#     bl_idname = "NODE_PT_omi_scene_audio_sources"
#     bl_parent_id = "NODE_PT_omi_scene_extensions"
#     bl_space_type = 'PROPERTIES'
#     bl_region_type = 'WINDOW'
#     bl_context = 'scene'
# 
#     def draw(self, context):
#         layout = self.layout
#         for clip in context.scene.OMI_audio_sources.value:
#             box = layout.box()
#             row = box.row()
#             preview_operator = row.operator("wm.omi_preview_audio", icon="PLAY")
#             preview_operator.source = clip.index
#             remove_operator = row.operator("wm.remove_audio_source", icon="X")
#             remove_operator.source = clip.index
#             box.prop(clip, 'name')
#             box.prop(clip, 'filename')
#             #layout.separator()
#         layout.operator(
#             "wm.add_audio_source",
#             text="Add Audio Clip",
#             icon="ADD"
#         )
# 
# class SceneEmitterPanel(bpy.types.Panel):
#     bl_label = 'Audio Emitter'
#     bl_idname = "NODE_PT_omi_scene_audio_emitter"
#     bl_parent_id = "NODE_PT_omi_scene_extensions"
#     bl_space_type = 'PROPERTIES'
#     # bl_options = {'HIDE_HEADER'}
#     bl_region_type = 'WINDOW'
#     bl_context = 'scene'
#     def draw(self, context):
#         ObjectEmitterPanel._draw(self, context, self.layout, context.scene)

### GLTF Export Screen
# class OMIAudioExtensionProperties(bpy.types.PropertyGroup):
#   enabled: bpy.props.BoolProperty(
#         name="Export OMI Audio Components",
#         description='Include this extension in the exported glTF file.',
#         default=True
#     )

class OMIAudioGLTFExportPanel(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "OMI Audio"
    bl_idname = "OMIGLTF_PT_export_omi_audio_extension"
    bl_parent_id = "OMIGLTF_PT_export_user_extensions"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return True or operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    # enabled = bpy.props.BoolProperty(name="enabled")
    def draw_header(self, context):
        pass
        #self.layout.prop(self.enabled, 'enabled', text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        pairs = OMIAudioEmitterExtension.gatherPairs(context)
        layout.active = context.scene.OMIExtensions.enabled

        box = layout.box()
        if len(pairs) == 0:
            box.label(text="(scene has no audio clips)")

        for d in [d for d in pairs if d.source.filename]:
            box.label(text=d.source.filename)

###########################################################################
# temporary testing -- env OMI_DEBUG=1 blender....
def omi_emitter_debug():
    scene = bpy.context.scene
    if hasattr(scene, 'OMI_audio_sources') and len(scene.OMI_audio_sources.value) == 0:
        print("Adding test clip", scene.OMI_audio_sources.value)
        clip = scene.OMI_audio_sources.value.add()
        clip.name = "test clip"
        clip.filename = "test_clip.mp3"






# def hashObject(context, object):
#     return str(object.as_pointer())
# 
# def findObjectByHash(context, ptr):
#     if hashObject(context.scene) == ptr:
#         return context.scene
#     for obj in bpy.data.objects:
#         if hashObject(obj) == ptr:
#             return obj
#     return None
# 
